from __future__ import annotations

from pathlib import Path
from collections import defaultdict
import socket
import time

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime
from engine.command_server import start_command_server


BASE_DIR = Path(__file__).resolve().parents[2]
HOST = "127.0.0.1"
PORT = 5557


# --------------------------------------------------
# TCP helper
# --------------------------------------------------

def send_cmd(cmd: str) -> str:
    with socket.create_connection((HOST, PORT), timeout=2) as s:
        s.sendall((cmd + "\n").encode("utf-8"))
        return s.recv(4096).decode("utf-8").strip()


def parse_value(line: str, key: str) -> float:
    for tok in line.split():
        if tok.startswith(f"{key}="):
            return float(tok.split("=", 1)[1])
    raise ValueError(f"Could not parse {key} from: {line}")


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
    # MD relay probe (population-level)
    # --------------------------------------------------
    PROBE_STEPS = 300
    MD_DRIVE = 0.04  # sub-decisional

    history = defaultdict(list)

    for step in range(PROBE_STEPS):
        # lawful external perturbation
        send_cmd(f"poke md {MD_DRIVE}")
        runtime.step()

        a_stats = send_cmd("stats_pop pfc L5_POLICY_A")
        b_stats = send_cmd("stats_pop pfc L5_POLICY_B")
        delta = send_cmd("delta_pop pfc L5_POLICY_A L5_POLICY_B")

        mean_a = parse_value(a_stats, "MEAN")
        mean_b = parse_value(b_stats, "MEAN")
        delta_act = parse_value(delta, "ΔACT")
        delta_out = parse_value(delta, "ΔOUT")

        history["A"].append(mean_a)
        history["B"].append(mean_b)
        history["delta_act"].append(delta_act)
        history["delta_out"].append(delta_out)

        if step % 25 == 0:
            print(
                f"[STEP {step:03d}] "
                f"A={mean_a:.6f} "
                f"B={mean_b:.6f} "
                f"ΔACT={delta_act:.6f} "
                f"ΔOUT={delta_out:.6f}"
            )

    # --------------------------------------------------
    # Summary (observational only)
    # --------------------------------------------------
    print("\n=== POLICY POPULATION DELTA SUMMARY ===")
    print(f"Mean ΔACT: {sum(history['delta_act']) / len(history['delta_act']):.6f}")
    print(f"Max  ΔACT: {max(history['delta_act']):.6f}")
    print(f"Mean ΔOUT: {sum(history['delta_out']) / len(history['delta_out']):.6f}")
    print(f"Max  ΔOUT: {max(history['delta_out']):.6f}")
    print("No decisions expected or checked.")
    print("======================================")


if __name__ == "__main__":
    main()
