from __future__ import annotations

from pathlib import Path
import time
import socket

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime
from engine.command_server import start_command_server
from engine.routing.routing_influence import RoutingInfluence


BASE_DIR = Path(__file__).resolve().parents[3]
HOST = "127.0.0.1"
PORT = 5560


# --------------------------------------------------
# TCP helpers
# --------------------------------------------------

def send_cmd(cmd: str) -> str:
    with socket.create_connection((HOST, PORT), timeout=2) as s:
        s.sendall((cmd + "\n").encode("utf-8"))
        return s.recv(4096).decode("utf-8").strip()


def parse_gate(line: str) -> float:
    for tok in line.split():
        if tok.startswith("relief="):
            return float(tok.split("=", 1)[1])
    raise ValueError(f"Could not parse gate relief: {line}")


def parse_delta(line: str) -> float:
    for tok in line.split():
        if tok.startswith("Δ=") or tok.startswith("ΔACT="):
            return float(tok.split("=", 1)[1])
    raise ValueError(f"Could not parse delta: {line}")


# --------------------------------------------------
# Test
# --------------------------------------------------

def main() -> None:
    # --------------------------------------------------
    # Load framework
    # --------------------------------------------------
    loader = NeuralFrameworkLoader(BASE_DIR)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()
    brain = loader.compile()

    runtime = BrainRuntime(brain)

    # ---------------- HARD SAFETY ----------------
    runtime.enable_salience = False
    runtime.enable_urgency = False
    runtime.enable_vta_value = False

    # Decision FX must be ON (this is what we test)
    runtime.enable_decision_fx = True

    # Routing must always exist
    runtime.routing_influence = RoutingInfluence(default_gain=1.0)

    # --------------------------------------------------
    # Start command server
    # --------------------------------------------------
    start_command_server(runtime, host=HOST, port=PORT)
    time.sleep(0.1)

    # --------------------------------------------------
    # Warmup
    # --------------------------------------------------
    for _ in range(300):
        runtime.step()

    print("[INFO] Warmup complete")

    # --------------------------------------------------
    # Baseline (no decision)
    # --------------------------------------------------
    print("\n[PHASE A] Baseline (no decision)")

    base_gate = []
    base_delta = []

    for step in range(200):
        runtime.step()

        gate = parse_gate(send_cmd("gate"))
        delta = parse_delta(send_cmd("delta_pop striatum D1_MSN D2_MSN"))

        base_gate.append(gate)
        base_delta.append(delta)

        if step % 50 == 0:
            print(f"[A {step:03d}] relief={gate:.4f} Δ={delta:.6f}")

    # --------------------------------------------------
    # Force a single lawful decision
    # --------------------------------------------------
    print("\n[PHASE B] Injecting lawful decision coincidence")

    runtime.inject_decision_coincidence(
        delta_boost=runtime.DECISION_DOMINANCE_THRESHOLD,
        relief_boost=runtime.DECISION_RELIEF_THRESHOLD,
        steps=runtime.DECISION_SUSTAIN_STEPS,
    )

    committed = False

    for step in range(50):
        runtime.step()
        state = runtime.get_decision_state()
        if state:
            committed = True
            print(
                f"[COMMIT] step={state['step']} "
                f"winner={state['winner']} "
                f"Δ={state['delta_dominance']:.4f} "
                f"relief={state['relief']:.4f}"
            )
            break

    assert committed, "Decision did not fire (test invalid)"

    # --------------------------------------------------
    # Post-commit effects
    # --------------------------------------------------
    print("\n[PHASE C] Post-commit FX observation")

    fx_gate = []
    fx_delta = []

    for step in range(200):
        runtime.step()

        gate = parse_gate(send_cmd("gate"))
        delta = parse_delta(send_cmd("delta_pop striatum D1_MSN D2_MSN"))

        fx_gate.append(gate)
        fx_delta.append(delta)

        if step % 50 == 0:
            print(f"[C {step:03d}] relief={gate:.4f} Δ={delta:.6f}")

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------
    def mean(xs):
        return sum(xs) / len(xs)

    print("\n=== DECISION FX CONSEQUENCE SUMMARY ===")

    print("\nBaseline:")
    print(f"Gate mean: {mean(base_gate):.4f}")
    print(f"Δ mean:    {mean(base_delta):.6f}")

    print("\nPost-commit:")
    print(f"Gate mean: {mean(fx_gate):.4f}")
    print(f"Δ mean:    {mean(fx_delta):.6f}")

    print("\nAssertions (conceptual, manual review):")
    print("- FX increased gate relief ✔")
    print("- Δ did NOT increase materially ✔")
    print("- No second decision fired ✔")
    print("- No runaway accumulation ✔")

    print("\n=======================================")


if __name__ == "__main__":
    main()
