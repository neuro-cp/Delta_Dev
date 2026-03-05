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
PORT = 5562


# --------------------------------------------------
# TCP helpers
# --------------------------------------------------

def send_cmd(cmd: str) -> str:
    with socket.create_connection((HOST, PORT), timeout=2) as s:
        s.sendall((cmd + "\n").encode("utf-8"))
        return s.recv(4096).decode("utf-8").strip()


def parse_mean(line: str) -> float:
    """
    Expected format:
    REGION:POP MASS=... MEAN=0.0158 STD=... N=...
    """
    for tok in line.split():
        if tok.upper().startswith("MEAN="):
            return float(tok.split("=", 1)[1])
    raise ValueError(f"Could not parse MEAN from: {line}")


def parse_delta(line: str) -> float:
    """
    Expected formats:
    ΔACT=...
    ΔOUT=...
    """
    for tok in line.split():
        if tok.startswith("ΔACT=") or tok.startswith("ΔOUT="):
            return float(tok.split("=", 1)[1])
    raise ValueError(f"Could not parse Δ from: {line}")


def parse_gate(line: str) -> float:
    """
    Expected format:
    relief=0.42
    """
    for tok in line.split():
        if tok.startswith("relief="):
            return float(tok.split("=", 1)[1])
    raise ValueError(f"Could not parse relief from: {line}")


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

    # Hard safety: FX only
    runtime.enable_vta_value = False
    runtime.enable_urgency = False
    runtime.enable_salience = False
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

    hist = defaultdict(list)

    # --------------------------------------------------
    # Phase A — Baseline
    # --------------------------------------------------
    print("\n[PHASE A] Baseline")

    for step in range(200):
        runtime.step()

        hist["A_pfc"].append(
            parse_mean(send_cmd("stats_pop pfc L2_3_PYRAMIDAL"))
        )
        hist["A_assoc"].append(
            parse_mean(send_cmd("stats_pop association_cortex L2_3_PYRAMIDAL"))
        )
        hist["A_v1"].append(
            parse_mean(send_cmd("stats_pop v1 L2_3_PYRAMIDAL"))
        )
        hist["A_delta"].append(
            parse_delta(send_cmd("delta_pop striatum D1_MSN D2_MSN"))
        )
        hist["A_gate"].append(
            parse_gate(send_cmd("gate"))
        )

    # --------------------------------------------------
    # Phase B — Lawful commit
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
    # Phase C — FX scope & targeting
    # --------------------------------------------------
    print("\n[PHASE C] FX scope & targeting")

    for step in range(300):
        runtime.step()

        hist["C_pfc"].append(
            parse_mean(send_cmd("stats_pop pfc L2_3_PYRAMIDAL"))
        )
        hist["C_assoc"].append(
            parse_mean(send_cmd("stats_pop association_cortex L2_3_PYRAMIDAL"))
        )
        hist["C_v1"].append(
            parse_mean(send_cmd("stats_pop v1 L2_3_PYRAMIDAL"))
        )
        hist["C_delta"].append(
            parse_delta(send_cmd("delta_pop striatum D1_MSN D2_MSN"))
        )
        hist["C_gate"].append(
            parse_gate(send_cmd("gate"))
        )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------
    def mean(xs):
        return sum(xs) / len(xs)

    print("\n=== DECISION FX SCOPE & TARGETING SUMMARY ===")

    print("\nBaseline → Post-commit:")
    print(f"PFC mean:   {mean(hist['A_pfc']):.6f} → {mean(hist['C_pfc']):.6f}")
    print(f"ASSOC mean: {mean(hist['A_assoc']):.6f} → {mean(hist['C_assoc']):.6f}")
    print(f"V1 mean:    {mean(hist['A_v1']):.6f} → {mean(hist['C_v1']):.6f}")
    print(f"Δ mean:     {mean(hist['A_delta']):.6f} → {mean(hist['C_delta']):.6f}")
    print(f"Gate mean:  {mean(hist['A_gate']):.6f} → {mean(hist['C_gate']):.6f}")

    print("\nExpected:")
    print("- Gate ↑ (FX advisory)")
    print("- Δ unchanged (no re-selection)")
    print("- Cortex stable (no leakage)")
    print("- No second decision")

    print("============================================")


if __name__ == "__main__":
    main()
