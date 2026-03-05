from __future__ import annotations

from pathlib import Path
from collections import defaultdict
import socket
import time

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime
from engine.command_server import start_command_server
from engine.routing.routing_influence import RoutingInfluence


BASE_DIR = Path(__file__).resolve().parents[3]
HOST = "127.0.0.1"
PORT = 5557


# --------------------------------------------------
# TCP helpers
# --------------------------------------------------

def send_cmd(cmd: str) -> str:
    with socket.create_connection((HOST, PORT), timeout=2) as s:
        s.sendall((cmd + "\n").encode("utf-8"))
        return s.recv(4096).decode("utf-8").strip()


def parse_mean(line: str) -> float:
    for tok in line.split():
        if tok.startswith("mean=") or tok.startswith("MEAN="):
            return float(tok.split("=", 1)[1])
    raise ValueError(f"Could not parse mean from: {line}")


def parse_delta(line: str) -> float:
    for tok in line.split():
        if tok.startswith("Δ=") or tok.startswith("ΔACT="):
            return float(tok.split("=", 1)[1])
    raise ValueError(f"Could not parse delta from: {line}")


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

    # Hard safety: disable higher systems
    runtime.enable_vta_value = False
    runtime.enable_urgency = False
    runtime.enable_decision_fx = False

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
    for _ in range(200):
        runtime.step()

    print("[INFO] Warmup complete")

    # Clear salience just to be explicit
    send_cmd("salience_clear")

    hist = defaultdict(list)

    # --------------------------------------------------
    # Phase A — Baseline (no pulvinar drive)
    # --------------------------------------------------
    print("\n[PHASE A] Baseline (no pulvinar stimulation)")

    for step in range(300):
        runtime.step()

        v1 = parse_mean(send_cmd("stats_pop v1 L2_3_PYRAMIDAL"))
        s1 = parse_mean(send_cmd("stats_pop s1 L2_3_PYRAMIDAL"))
        assoc = parse_mean(send_cmd("stats_pop association_cortex L2_3_PYRAMIDAL"))
        delta = parse_delta(send_cmd("delta_pop striatum D1_MSN D2_MSN"))

        hist["A_v1"].append(v1)
        hist["A_s1"].append(s1)
        hist["A_assoc"].append(assoc)
        hist["A_delta"].append(delta)

        if step % 50 == 0:
            print(
                f"[A {step:03d}] "
                f"V1={v1:.6f} "
                f"S1={s1:.6f} "
                f"ASSOC={assoc:.6f} "
                f"Δ={delta:.6f}"
            )

    # --------------------------------------------------
    # Phase B — Pulvinar relay active
    # --------------------------------------------------
    print("\n[PHASE B] Pulvinar relay active (poke pulvinar 1.0)")

    for step in range(300):
        send_cmd("poke pulvinar 1.0")
        runtime.step()

        v1 = parse_mean(send_cmd("stats_pop v1 L2_3_PYRAMIDAL"))
        s1 = parse_mean(send_cmd("stats_pop s1 L2_3_PYRAMIDAL"))
        assoc = parse_mean(send_cmd("stats_pop association_cortex L2_3_PYRAMIDAL"))
        delta = parse_delta(send_cmd("delta_pop striatum D1_MSN D2_MSN"))

        hist["B_v1"].append(v1)
        hist["B_s1"].append(s1)
        hist["B_assoc"].append(assoc)
        hist["B_delta"].append(delta)

        if step % 50 == 0:
            print(
                f"[B {step:03d}] "
                f"V1={v1:.6f} "
                f"S1={s1:.6f} "
                f"ASSOC={assoc:.6f} "
                f"Δ={delta:.6f}"
            )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------
    def summarize(label, data):
        return sum(data) / len(data)

    print("\n=== PULVINAR RELAY CHARACTERIZATION SUMMARY ===")

    print("\nPhase A (baseline):")
    print(f"V1 mean:    {summarize('A_v1', hist['A_v1']):.6f}")
    print(f"S1 mean:    {summarize('A_s1', hist['A_s1']):.6f}")
    print(f"ASSOC mean: {summarize('A_assoc', hist['A_assoc']):.6f}")
    print(f"Δ mean:     {summarize('A_delta', hist['A_delta']):.6f}")

    print("\nPhase B (pulvinar active):")
    print(f"V1 mean:    {summarize('B_v1', hist['B_v1']):.6f}")
    print(f"S1 mean:    {summarize('B_s1', hist['B_s1']):.6f}")
    print(f"ASSOC mean: {summarize('B_assoc', hist['B_assoc']):.6f}")
    print(f"Δ mean:     {summarize('B_delta', hist['B_delta']):.6f}")

    print("\nNo decisions expected or checked.")
    print("===============================================")


if __name__ == "__main__":
    main()
