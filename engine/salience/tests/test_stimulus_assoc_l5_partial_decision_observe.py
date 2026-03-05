# engine/salience/tests/test_stimulus_assoc_l5_partial_decision_observe.py

from __future__ import annotations

import time
from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime
from engine.command_server import start_command_server


# ============================================================
# CONFIG
# ============================================================

DT = 0.01
TOTAL_STEPS = 1200

STIM_START = 100
STIM_END   = 600

STIM_GAIN = 0.15
STIM_FRACTION = 0.20   # 20% of L5_A assemblies

TARGET_REGION = "association_cortex"
TARGET_POP    = "L5_PYRAMIDAL_A"


# ============================================================
# TEST
# ============================================================

def main():

    base = Path(__file__).resolve().parents[3]

    loader = NeuralFrameworkLoader(base)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile()

    runtime = BrainRuntime(brain, dt=DT)

    # --------------------------------------------------------
    # Salience already attached by prior work
    # --------------------------------------------------------

    # --------------------------------------------------------
    # Identify target assemblies
    # --------------------------------------------------------
    region = runtime.region_states[TARGET_REGION]
    pops = region["populations"][TARGET_POP]

    total = len(pops)
    k = max(1, int(total * STIM_FRACTION))
    target_assemblies = pops[:k]

    print(f"[INIT] Stimulating {k}/{total} {TARGET_REGION}:{TARGET_POP} assemblies")

    # --------------------------------------------------------
    # Command server (optional live inspection)
    # --------------------------------------------------------
    start_command_server(runtime, port=5562)

    # --------------------------------------------------------
    # Run
    # --------------------------------------------------------
    for step in range(TOTAL_STEPS):

        stim_on = STIM_START <= step < STIM_END

        if stim_on:
            for p in target_assemblies:
                runtime.inject_stimulus(
                    TARGET_REGION,
                    TARGET_POP,
                    assembly_index=int(p.assembly_id.split(":")[-1]),
                    magnitude=STIM_GAIN,
                )

        runtime.step()

        if step % 50 == 0:
            snap = getattr(runtime, "_last_striatum_snapshot", {})
            dom = snap.get("dominance", {})

            delta = 0.0
            if len(dom) >= 2:
                vals = sorted(dom.values(), reverse=True)
                delta = vals[0] - vals[1]

            gate = runtime.snapshot_gate_state()
            decision = runtime.get_decision_state()

            print(
                f"[STEP {step:04d}] "
                f"Δ={delta:.6f} "
                f"relief={gate['relief']:.4f} "
                f"stim={'ON' if stim_on else 'OFF'} "
                f"decision={decision}"
            )

        if runtime.get_decision_state() is not None:
            print("\n=== DECISION FIRED ===")
            print(runtime.get_decision_state())
            break

        time.sleep(0.002)

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()
