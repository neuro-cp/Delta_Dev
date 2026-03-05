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


def parse_delta(line: str) -> tuple[float, float]:
    d_act = None
    d_out = None

    for tok in line.split():
        if tok.startswith("ΔACT="):
            d_act = float(tok.split("=", 1)[1])
        elif tok.startswith("ΔOUT="):
            d_out = float(tok.split("=", 1)[1])

    if d_act is None or d_out is None:
        raise ValueError(f"Could not parse delta_pop output: {line}")

    return d_act, d_out


# --------------------------------------------------
# Summary helper
# --------------------------------------------------

def summarize(label: str, hist: dict) -> None:
    mean_act = sum(hist["d_act"]) / len(hist["d_act"])
    max_act = max(hist["d_act"])
    mean_out = sum(hist["d_out"]) / len(hist["d_out"])
    max_out = max(hist["d_out"])

    print(f"\n=== {label} SUMMARY ===")
    print(f"Mean ΔACT: {mean_act:.6f}")
    print(f"Max  ΔACT: {max_act:.6f}")
    print(f"Mean ΔOUT: {mean_out:.6f}")
    print(f"Max  ΔOUT: {max_out:.6f}")


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

    runtime.enable_vta_value = False
    runtime.enable_urgency = False
    runtime.enable_decision_fx = False

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
    # Structural salience setup
    # --------------------------------------------------
    send_cmd("salience_clear")
    send_cmd("salience_set pfc:L2_3_PYRAMIDAL:0 0.6")

    # --------------------------------------------------
    # ABABAB cycles
    # --------------------------------------------------
    CYCLES = 3
    STEPS = 300

    for cycle in range(1, CYCLES + 1):
        print(f"\n==============================")
        print(f"       CYCLE {cycle}")
        print(f"==============================")

        # ---------- Phase A ----------
        runtime.routing_influence = RoutingInfluence(default_gain=1.0)
        hist_A = defaultdict(list)

        print("[PHASE A] Routing influence OFF (identity)")

        for step in range(STEPS):
            send_cmd("poke md 0.04")
            runtime.step()

            line = send_cmd("delta_pop striatum D1_MSN D2_MSN")
            d_act, d_out = parse_delta(line)

            hist_A["d_act"].append(d_act)
            hist_A["d_out"].append(d_out)

            if step % 25 == 0:
                print(f"[A{cycle} {step:03d}] ΔACT={d_act:.6f} ΔOUT={d_out:.6f}")

        summarize(f"CYCLE {cycle} – PHASE A", hist_A)

        # ---------- Phase B ----------
        runtime.routing_influence = RoutingInfluence()
        hist_B = defaultdict(list)

        print("[PHASE B] Routing influence ON")

        for step in range(STEPS):
            send_cmd("poke md 0.04")
            runtime.step()

            line = send_cmd("delta_pop striatum D1_MSN D2_MSN")
            d_act, d_out = parse_delta(line)

            hist_B["d_act"].append(d_act)
            hist_B["d_out"].append(d_out)

            if step % 25 == 0:
                print(f"[B{cycle} {step:03d}] ΔACT={d_act:.6f} ΔOUT={d_out:.6f}")

        summarize(f"CYCLE {cycle} – PHASE B", hist_B)

    print("\nNo decisions expected or checked.")
    print("===================================")


if __name__ == "__main__":
    main()
