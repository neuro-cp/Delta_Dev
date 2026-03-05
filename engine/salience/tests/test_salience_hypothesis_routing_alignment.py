# engine/salience/tests/test_salience_hypothesis_routing_alignment.py
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
# TCP helper
# --------------------------------------------------

def send_cmd(cmd: str) -> str:
    with socket.create_connection((HOST, PORT), timeout=2) as s:
        s.sendall((cmd + "\n").encode("utf-8"))
        return s.recv(4096).decode("utf-8").strip()


def parse_delta(line: str) -> tuple[float, float]:
    d_act = d_out = None
    for tok in line.split():
        if tok.startswith("ΔACT="):
            d_act = float(tok.split("=", 1)[1])
        elif tok.startswith("ΔOUT="):
            d_out = float(tok.split("=", 1)[1])
    if d_act is None or d_out is None:
        raise ValueError(f"Could not parse delta_pop output: {line}")
    return d_act, d_out


# --------------------------------------------------
# Test
# --------------------------------------------------

def run_phase(label: str, runtime: BrainRuntime, steps: int = 300):
    hist = defaultdict(list)
    print(f"\n[{label}]")

    for step in range(steps):
        send_cmd("poke md 0.04")
        runtime.step()

        line = send_cmd("delta_pop striatum D1_MSN D2_MSN")
        d_act, d_out = parse_delta(line)

        hist["d_act"].append(d_act)
        hist["d_out"].append(d_out)

        if step % 25 == 0:
            print(f"[{label} {step:03d}] ΔACT={d_act:.6f} ΔOUT={d_out:.6f}")

    return hist


def summarize(label: str, hist):
    print(f"\n=== {label} SUMMARY ===")
    print(f"Mean ΔACT: {sum(hist['d_act']) / len(hist['d_act']):.6f}")
    print(f"Max  ΔACT: {max(hist['d_act']):.6f}")
    print(f"Mean ΔOUT: {sum(hist['d_out']) / len(hist['d_out']):.6f}")
    print(f"Max  ΔOUT: {max(hist['d_out']):.6f}")


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

    # Safety
    runtime.enable_vta_value = False
    runtime.enable_urgency = False
    runtime.enable_decision_fx = False

    # Routing influence always present (identity default)
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
    # Structural salience
    # --------------------------------------------------
    send_cmd("salience_clear")

    TARGET_ASM = "pfc:L2_3_PYRAMIDAL:0"
    send_cmd(f"salience_set {TARGET_ASM} 0.6")

    # --------------------------------------------------
    # Phase A: no hypothesis (baseline)
    # --------------------------------------------------
    send_cmd("hypothesis_reset")
    hist_A = run_phase("BASELINE (no hypothesis)", runtime)

    # --------------------------------------------------
    # Phase B: aligned hypothesis (D1)
    # --------------------------------------------------
    send_cmd("hypothesis_reset")
    send_cmd(f"hypothesis_set {TARGET_ASM} D1")
    hist_B = run_phase("ALIGNED (hypothesis = D1)", runtime)

    # --------------------------------------------------
    # Phase C: misaligned hypothesis (D2)
    # --------------------------------------------------
    send_cmd("hypothesis_reset")
    send_cmd(f"hypothesis_set {TARGET_ASM} D2")
    hist_C = run_phase("MISALIGNED (hypothesis = D2)", runtime)

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------
    summarize("BASELINE", hist_A)
    summarize("ALIGNED", hist_B)
    summarize("MISALIGNED", hist_C)

    print("\nNo decisions expected or checked.")
    print("===================================")


if __name__ == "__main__":
    main()
