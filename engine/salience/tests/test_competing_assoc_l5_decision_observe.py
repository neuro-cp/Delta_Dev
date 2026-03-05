from __future__ import annotations

import time
from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime
from engine.command_server import start_command_server


DT = 0.01
TOTAL_STEPS = 1400

A_START, A_END = 100, 600
B_START, B_END = 300, 800

STIM_GAIN_A = 0.01
STIM_GAIN_B = 0.9

REGION = "association_cortex"
POP_A = "L5_PYRAMIDAL_A"
POP_B = "L5_PYRAMIDAL_B"


def main():

    base = Path(__file__).resolve().parents[3]

    loader = NeuralFrameworkLoader(base)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile()
    runtime = BrainRuntime(brain, dt=DT)

    reg = runtime.region_states[REGION]
    pops_a = reg["populations"][POP_A][:40]
    pops_b = reg["populations"][POP_B][:40]

    print(f"[INIT] Competing stimuli: {POP_A} vs {POP_B}")

    start_command_server(runtime, port=5563)

    for step in range(TOTAL_STEPS):

        if A_START <= step < A_END:
            for p in pops_a:
                runtime.inject_stimulus(
                    REGION, POP_A,
                    int(p.assembly_id.split(":")[-1]),
                    STIM_GAIN_A
                )

        if B_START <= step < B_END:
            for p in pops_b:
                runtime.inject_stimulus(
                    REGION, POP_B,
                    int(p.assembly_id.split(":")[-1]),
                    STIM_GAIN_B
                )

        runtime.step()

        if step % 50 == 0:
            snap = getattr(runtime, "_last_striatum_snapshot", {})
            dom = snap.get("dominance", {})

            delta = 0.0
            if len(dom) >= 2:
                v = sorted(dom.values(), reverse=True)
                delta = v[0] - v[1]

            gate = runtime.snapshot_gate_state()
            dec = runtime.get_decision_state()

            print(
                f"[STEP {step:04d}] "
                f"Δ={delta:.6f} "
                f"relief={gate['relief']:.4f} "
                f"A={'ON' if A_START <= step < A_END else 'OFF'} "
                f"B={'ON' if B_START <= step < B_END else 'OFF'} "
                f"decision={dec}"
            )

        if runtime.get_decision_state() is not None:
            print("\n=== DECISION FIRED ===")
            print(runtime.get_decision_state())
            break

        time.sleep(0.002)

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()
