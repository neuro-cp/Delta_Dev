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
PORT = 5563


# --------------------------------------------------
# TCP helpers
# --------------------------------------------------

def send_cmd(cmd: str) -> str:
    with socket.create_connection((HOST, PORT), timeout=2) as s:
        s.sendall((cmd + "\n").encode("utf-8"))
        return s.recv(4096).decode("utf-8").strip()


def parse_mean(line: str) -> float:
    for tok in line.split():
        k, _, v = tok.partition("=")
        if k.lower() == "mean":
            return float(v)
    raise ValueError(f"Could not parse MEAN from: {line}")


def parse_gate(line: str) -> float:
    for tok in line.split():
        if tok.startswith("relief="):
            return float(tok.split("=", 1)[1])
    raise ValueError(line)


def parse_delta(line: str) -> float:
    for tok in line.split():
        if tok.startswith("ΔACT=") or tok.startswith("ΔOUT="):
            return float(tok.split("=", 1)[1])
    raise ValueError(line)


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

    # Freeze unrelated systems
    runtime.enable_vta_value = False
    runtime.enable_urgency = False
    runtime.enable_salience = False
    runtime.enable_decision_fx = True   # FX must be on
    runtime.routing_influence = RoutingInfluence(default_gain=1.0)

    start_command_server(runtime, host=HOST, port=PORT)
    time.sleep(0.1)

    # --------------------------------------------------
    # Warmup
    # --------------------------------------------------
    for _ in range(200):
        runtime.step()

    print("[INFO] Warmup complete")

    hist = defaultdict(list)

    # --------------------------------------------------
    # Phase A — Baseline (no decision, no working state)
    # --------------------------------------------------
    print("\n[PHASE A] Baseline")

    for _ in range(200):
        runtime.step()

        hist["A_pfc"].append(parse_mean(send_cmd("stats_pop pfc L2_3_PYRAMIDAL")))
        hist["A_gate"].append(parse_gate(send_cmd("gate")))
        hist["A_delta"].append(parse_delta(send_cmd("delta_pop striatum D1_MSN D2_MSN")))
        hist["A_control"].append(send_cmd("control"))

    # --------------------------------------------------
    # Phase B — Lawful decision commit
    # --------------------------------------------------
    print("\n[PHASE B] Injecting lawful decision coincidence")

    runtime.inject_decision_coincidence(
        delta_boost=runtime.DECISION_DOMINANCE_THRESHOLD,
        relief_boost=runtime.DECISION_RELIEF_THRESHOLD,
        steps=5,
    )

    while not runtime.get_decision_state():
        runtime.step()

    dec = runtime.get_decision_state()
    print(
        f"[COMMIT] step={dec['step']} "
        f"winner={dec['winner']} "
        f"Δ={dec['delta_dominance']:.4f} "
        f"relief={dec['relief']:.4f}"
    )

    # --------------------------------------------------
    # Phase C — Working-state authority (hold)
    # --------------------------------------------------
    print("\n[PHASE C] Working-state authority window")

    for _ in range(300):
        runtime.step()

        hist["C_pfc"].append(parse_mean(send_cmd("stats_pop pfc L2_3_PYRAMIDAL")))
        hist["C_gate"].append(parse_gate(send_cmd("gate")))
        hist["C_delta"].append(parse_delta(send_cmd("delta_pop striatum D1_MSN D2_MSN")))
        hist["C_control"].append(send_cmd("control"))

    # --------------------------------------------------
    # Phase D — Release & decay
    # --------------------------------------------------
    print("\n[PHASE D] Working-state release")

    for _ in range(300):
        runtime.step()

        hist["D_pfc"].append(parse_mean(send_cmd("stats_pop pfc L2_3_PYRAMIDAL")))
        hist["D_gate"].append(parse_gate(send_cmd("gate")))
        hist["D_delta"].append(parse_delta(send_cmd("delta_pop striatum D1_MSN D2_MSN")))
        hist["D_control"].append(send_cmd("control"))

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------
    def mean(xs):
        return sum(xs) / len(xs)

    print("\n=== WORKING STATE AUTHORITY & RELEASE SUMMARY ===")

    print("\nBaseline:")
    print(f"PFC mean:  {mean(hist['A_pfc']):.6f}")
    print(f"Gate mean: {mean(hist['A_gate']):.6f}")
    print(f"Δ mean:    {mean(hist['A_delta']):.6f}")

    print("\nAuthority (post-commit):")
    print(f"PFC mean:  {mean(hist['C_pfc']):.6f}")
    print(f"Gate mean: {mean(hist['C_gate']):.6f}")
    print(f"Δ mean:    {mean(hist['C_delta']):.6f}")

    print("\nRelease:")
    print(f"PFC mean:  {mean(hist['D_pfc']):.6f}")
    print(f"Gate mean: {mean(hist['D_gate']):.6f}")
    print(f"Δ mean:    {mean(hist['D_delta']):.6f}")

    print("\nExpected:")
    print("- Working state engages post-commit")
    print("- Authority persists transiently")
    print("- Gate remains elevated but bounded")
    print("- Δ stays at noise floor")
    print("- Working state releases without re-decision")

    print("=================================================")


if __name__ == "__main__":
    main()
