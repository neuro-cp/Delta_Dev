from __future__ import annotations

from pathlib import Path
from collections import defaultdict
import socket
import time

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime
from engine.command_server import start_command_server


BASE_DIR = Path(__file__).resolve().parents[3]
HOST = "127.0.0.1"
PORT = 5557


# --------------------------------------------------
# TCP helper
# --------------------------------------------------

def send_cmd(cmd: str) -> str:
    with socket.create_connection((HOST, PORT), timeout=2) as s:
        s.sendall((cmd + "\n").encode("utf-8"))
        return s.recv(4096).decode("utf-8").strip()


def parse_delta(line: str) -> tuple[float, float]:
    """
    Extract ΔACT and ΔOUT from delta_pop output.
    """
    act = out = 0.0
    for tok in line.split():
        if tok.startswith("ΔACT="):
            act = float(tok.split("=", 1)[1])
        elif tok.startswith("ΔOUT="):
            out = float(tok.split("=", 1)[1])
    return act, out


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

    # Safety: explicitly disable higher systems
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
    # Salience-induced policy asymmetry probe
    # --------------------------------------------------
    PROBE_STEPS = 300
    MD_DRIVE = 0.04  # mild, sub-decisional

    history = defaultdict(list)

    for step in range(PROBE_STEPS):
        # lawful upstream perturbation
        send_cmd(f"poke md {MD_DRIVE}")
        runtime.step()

        # population delta (read-only)
        line = send_cmd(
            "delta_pop pfc L5_POLICY_A L5_POLICY_B"
        )

        d_act, d_out = parse_delta(line)

        history["d_act"].append(d_act)
        history["d_out"].append(d_out)

        if step % 25 == 0:
            print(
                f"[STEP {step:03d}] "
                f"ΔACT={d_act:.6f} "
                f"ΔOUT={d_out:.6f}"
            )

    # --------------------------------------------------
    # Summary (observational only)
    # --------------------------------------------------
    mean_d_act = sum(history["d_act"]) / len(history["d_act"])
    max_d_act = max(history["d_act"])

    mean_d_out = sum(history["d_out"]) / len(history["d_out"])
    max_d_out = max(history["d_out"])

    print("\n=== SALIENCE POLICY GATE SUMMARY ===")
    print(f"Mean ΔACT: {mean_d_act:.6f}")
    print(f"Max  ΔACT: {max_d_act:.6f}")
    print(f"Mean ΔOUT: {mean_d_out:.6f}")
    print(f"Max  ΔOUT: {max_d_out:.6f}")
    print("No decisions expected or checked.")
    print("===================================")


if __name__ == "__main__":
    main()
