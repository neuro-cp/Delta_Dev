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
SPARSITY_SEED = 43   # new seed, still deterministic

VALUE_MAG = 0.6
ENABLE_URGENCY = False


# ============================================================
# TEST
# ============================================================

def main():
    print("\n=== TEST: Salience MD + PFC L2/3 Extension (Observational) ===\n")

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
    # Configure subsystems (unchanged)
    # --------------------------------------------------
    runtime.enable_salience = True
    runtime.enable_vta_value = True
    runtime.enable_urgency = ENABLE_URGENCY

    runtime.value_set(VALUE_MAG)

    # --------------------------------------------------
    # Collect MD assemblies
    # --------------------------------------------------
    md_state = runtime.region_states.get("md")
    assert md_state is not None, "MD region not found"

    md_assemblies = [
        p.assembly_id
        for plist in md_state["populations"].values()
        for p in plist
    ]

    print(f"[INIT] MD assemblies: {len(md_assemblies)}")

    # --------------------------------------------------
    # Collect PFC L2/3 assemblies ONLY
    # --------------------------------------------------
    pfc_state = runtime.region_states.get("pfc")
    assert pfc_state is not None, "PFC region not found"

    l23 = pfc_state["populations"].get("L2_3_PYRAMIDAL")
    assert l23 is not None, "PFC L2_3_PYRAMIDAL not found"

    pfc_l23_assemblies = [p.assembly_id for p in l23]

    print(f"[INIT] PFC L2/3 assemblies: {len(pfc_l23_assemblies)}")

    # --------------------------------------------------
    # Attach salience sparsity gate (MD + PFC L2/3)
    # --------------------------------------------------
    all_assemblies = md_assemblies + pfc_l23_assemblies

    gate = SalienceSparsityGate(
        keep_ratio=KEEP_RATIO,
        seed=SPARSITY_SEED,
    )

    gate.initialize(all_assemblies)
    runtime.salience.attach_sparsity_gate(gate)

    print("[INIT] Salience sparsity gate attached to MD + PFC L2/3")
    print("[INIT] Gate stats:", gate.stats())

    # --------------------------------------------------
    # Optional live inspection
    # --------------------------------------------------
    start_command_server(runtime, port=5559)
    print("[INFO] Command server on port 5559")

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
