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
        if tok.lower().startswith("mean="):
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

    # --------------------------------------------------
    # Structural salience cleared
    # --------------------------------------------------
    send_cmd("salience_clear")

    # --------------------------------------------------
    # Histories
    # --------------------------------------------------
    hist = defaultdict(list)

    # --------------------------------------------------
    # Phase A — No TRN suppression
    # --------------------------------------------------
    print("\n[PHASE A] Baseline MD relay (no TRN suppression)")

    for step in range(300):
        send_cmd("poke md 0.04")
        runtime.step()

        pfc_line = send_cmd("stats_pop pfc L2_3_PYRAMIDAL")
        delta_line = send_cmd("delta_pop striatum D1_MSN D2_MSN")

        pfc_mean = parse_mean(pfc_line)
        delta = parse_delta(delta_line)

        hist["A_pfc"].append(pfc_mean)
        hist["A_delta"].append(delta)

        if step % 25 == 0:
            print(f"[A {step:03d}] PFC mean={pfc_mean:.6f} Δ(D1–D2)={delta:.6f}")

    # --------------------------------------------------
    # Phase B — TRN suppression active
    # --------------------------------------------------
    print("\n[PHASE B] TRN suppression ON")

    for step in range(300):
        send_cmd("poke trn -0.10")
        send_cmd("poke md 0.04")
        runtime.step()

        pfc_line = send_cmd("stats_pop pfc L2_3_PYRAMIDAL")
        delta_line = send_cmd("delta_pop striatum D1_MSN D2_MSN")

        pfc_mean = parse_mean(pfc_line)
        delta = parse_delta(delta_line)

        hist["B_pfc"].append(pfc_mean)
        hist["B_delta"].append(delta)

        if step % 25 == 0:
            print(f"[B {step:03d}] PFC mean={pfc_mean:.6f} Δ(D1–D2)={delta:.6f}")

    # --------------------------------------------------
    # Summary (observational)
    # --------------------------------------------------
    def summarize(label, pfc, delta):
        print(f"\n=== {label} SUMMARY ===")
        print(f"Mean PFC activity: {sum(pfc)/len(pfc):.6f}")
        print(f"Max  PFC activity: {max(pfc):.6f}")
        print(f"Mean Δ(D1–D2): {sum(delta)/len(delta):.6f}")
        print(f"Max  Δ(D1–D2): {max(delta):.6f}")

    summarize("PHASE A (no TRN)", hist["A_pfc"], hist["A_delta"])
    summarize("PHASE B (TRN suppressed)", hist["B_pfc"], hist["B_delta"])

    print("\nNo decisions expected or checked.")
    print("================================")


if __name__ == "__main__":
    main()
