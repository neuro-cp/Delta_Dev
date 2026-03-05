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


def parse_stats(line: str) -> float:
    """
    Extract MEAN=<value> from `stats <region>` output.
    """
    for tok in line.split():
        if tok.startswith("MEAN="):
            return float(tok.split("=", 1)[1])
    raise ValueError(f"Could not parse MEAN from: {line}")


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

    # Hard safety: no higher systems
    runtime.enable_vta_value = False
    runtime.enable_urgency = False
    runtime.enable_decision_fx = False

    # Routing influence present but identity
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
    # Structural salience (single assembly)
    # --------------------------------------------------
    send_cmd("salience_clear")
    send_cmd("salience_set pfc:L2_3_PYRAMIDAL:0 0.6")

    # --------------------------------------------------
    # MD relay probe
    # --------------------------------------------------
    STEPS = 300
    MD_DRIVE = 0.04  # lawful, sub-decisional

    history = defaultdict(list)

    print("\n[MD RELAY → PFC LAYER FIDELITY TEST]")

    for step in range(STEPS):
        send_cmd(f"poke md {MD_DRIVE}")
        runtime.step()

        l23 = parse_stats(send_cmd("stats pfc"))
        l5a = parse_stats(send_cmd("stats pfc"))  # same region, layer split handled internally

        # policy deltas from striatum give us channel contrast
        delta_line = send_cmd("delta_pop striatum D1_MSN D2_MSN")
        d_act = None
        for tok in delta_line.split():
            if tok.startswith("ΔACT="):
                d_act = float(tok.split("=", 1)[1])

        history["l23"].append(l23)
        history["delta"].append(d_act or 0.0)

        if step % 25 == 0:
            print(
                f"[STEP {step:03d}] "
                f"PFC mean={l23:.6f} "
                f"Δ(D1–D2)={d_act:.6f}"
            )

    # --------------------------------------------------
    # Summary (observational only)
    # --------------------------------------------------
    print("\n=== MD RELAY FIDELITY SUMMARY ===")
    print(f"Mean PFC activity: {sum(history['l23']) / len(history['l23']):.6f}")
    print(f"Max  PFC activity: {max(history['l23']):.6f}")
    print(f"Mean Δ(D1–D2): {sum(history['delta']) / len(history['delta']):.6f}")
    print(f"Max  Δ(D1–D2): {max(history['delta']):.6f}")
    print("No decisions expected or checked.")
    print("================================")


if __name__ == "__main__":
    main()
