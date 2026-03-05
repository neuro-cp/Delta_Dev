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
STEPS = 1200

KEEP_RATIO = 0.25
SPARSITY_SEED = 45

VALUE_MAG = 0.6
ENABLE_URGENCY = False

# ---- Stimulus (lawful, weak, sustained) ----
STIM_REGION = "association_cortex"
STIM_POP    = "L5_PYRAMIDAL_A"

STIM_START = 100
STIM_END   = 600
STIM_GAIN  = 0.15   # deliberately conservative


# ============================================================
# TEST
# ============================================================

def main():
    print("\n=== TEST: Stimulus-Driven Asymmetry (Assoc Cortex L5_A) ===\n")

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
    # Enable subsystems (NO CHEATING)
    # --------------------------------------------------
    runtime.enable_salience = True
    runtime.enable_vta_value = True
    runtime.enable_urgency = ENABLE_URGENCY

    runtime.value_set(VALUE_MAG)

    # --------------------------------------------------
    # Collect salience adoption assemblies
    # --------------------------------------------------
    md    = runtime.region_states["md"]
    pfc   = runtime.region_states["pfc"]
    assoc = runtime.region_states["association_cortex"]

    assemblies = []

    # MD
    for plist in md["populations"].values():
        for p in plist:
            assemblies.append(p.assembly_id)

    # PFC L2/3
    for p in pfc["populations"]["L2_3_PYRAMIDAL"]:
        assemblies.append(p.assembly_id)

    # Association cortex
    for pop in ("L2_3_PYRAMIDAL", "L5_PYRAMIDAL_A", "L5_PYRAMIDAL_B"):
        for p in assoc["populations"][pop]:
            assemblies.append(p.assembly_id)

    gate = SalienceSparsityGate(
        keep_ratio=KEEP_RATIO,
        seed=SPARSITY_SEED,
    )

    gate.initialize(assemblies)
    runtime.salience.attach_sparsity_gate(gate)

    print("[INIT] Salience sparsity gate attached")
    print("[INIT] Gate stats:", gate.stats())

    # --------------------------------------------------
    # Stimulus target indices (lawful addressing)
    # --------------------------------------------------
    stim_indices = list(range(len(assoc["populations"][STIM_POP])))

    print(
        f"[INIT] Stimulating {len(stim_indices)} "
        f"{STIM_REGION}:{STIM_POP} assemblies"
    )

    # --------------------------------------------------
    # Optional live inspection
    # --------------------------------------------------
    start_command_server(runtime, port=5561)
    print("[INFO] Command server on port 5561")

    # --------------------------------------------------
    # Run
    # --------------------------------------------------
    for step in range(STEPS):

        # ---- External stimulus (Step 1 pathway only) ----
        if STIM_START <= step <= STIM_END:
            for idx in stim_indices:
                runtime.inject_stimulus(
                    STIM_REGION,
                    STIM_POP,
                    idx,
                    STIM_GAIN,
                )

        runtime.step()

        if step % 50 == 0:
            snap = getattr(runtime, "_last_striatum_snapshot", {}) or {}
            gate_state = runtime.snapshot_gate_state()

            delta = 0.0
            dom = snap.get("dominance", {})
            if len(dom) >= 2:
                vals = sorted(dom.values(), reverse=True)
                delta = vals[0] - vals[1]

            decision = runtime.get_decision_state()

            print(
                f"[STEP {step:04d}] "
                f"Δ={delta:.6f} "
                f"relief={gate_state.get('relief', 1.0):.4f} "
                f"stim={'ON' if STIM_START <= step <= STIM_END else 'OFF'} "
                f"decision={decision}"
            )

        time.sleep(0.0)

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()
