from __future__ import annotations

from pathlib import Path
from collections import defaultdict
import socket
import time

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime
from engine.command_server import start_command_server
from engine.routing.routing_influence import RoutingInfluence


BASE_DIR = Path(__file__).resolve().parents[2]
HOST = "127.0.0.1"
PORT = 5561


# --------------------------------------------------
# TCP helpers
# --------------------------------------------------

def send_cmd(cmd: str) -> str:
    with socket.create_connection((HOST, PORT), timeout=2) as s:
        s.sendall((cmd + "\n").encode("utf-8"))
        return s.recv(4096).decode("utf-8").strip()


def parse_gate_relief(line: str) -> float:
    """
    Parse gate relief from `gate` command.
    """
    for tok in line.split():
        if tok.startswith("relief="):
            return float(tok.split("=", 1)[1])
    raise ValueError(f"Could not parse relief from: {line}")


def parse_delta_out(line: str) -> float:
    """
    Parse downstream (behaviorally relevant) delta from delta_pop.
    """
    for tok in line.split():
        if tok.startswith("ΔOUT="):
            return float(tok.split("=", 1)[1])
    raise ValueError(f"Could not parse ΔOUT from: {line}")


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

    # Hard safety: freeze unrelated systems
    runtime.enable_vta_value = False
    runtime.enable_urgency = False
    runtime.enable_decision_fx = True   # required for Phase 4
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
    print("\n[PHASE A] Baseline (no decision)")

    for step in range(200):
        runtime.step()

        gate = parse_gate_relief(send_cmd("gate"))
        delta = parse_delta_out(
            send_cmd("delta_pop striatum D1_MSN D2_MSN")
        )
        control = send_cmd("control")

        hist["A_gate"].append(gate)
        hist["A_delta"].append(delta)
        hist["A_control"].append(control)

        if step % 50 == 0:
            print(f"[A {step:03d}] relief={gate:.4f} ΔOUT={delta:.6f}")

    # --------------------------------------------------
    # Phase B — Lawful commit
    # --------------------------------------------------
    print("\n[PHASE B] Injecting lawful decision coincidence")

    runtime.inject_decision_coincidence(
        delta_boost=runtime.DECISION_DOMINANCE_THRESHOLD,
        relief_boost=runtime.DECISION_RELIEF_THRESHOLD,
        steps=5,
    )

    committed = False
    for _ in range(100):
        runtime.step()
        dec = runtime.get_decision_state()
        if dec:
            print(
                f"[COMMIT] step={dec['step']} "
                f"winner={dec['winner']} "
                f"Δ={dec['delta_dominance']:.4f} "
                f"relief={dec['relief']:.4f}"
            )
            committed = True
            break

    if not committed:
        print("[WARN] Decision did not fire (unexpected)")

    # --------------------------------------------------
    # Phase C — Control persistence
    # --------------------------------------------------
    print("\n[PHASE C] Control persistence observation")

    for step in range(200):
        runtime.step()

        gate = parse_gate_relief(send_cmd("gate"))
        delta = parse_delta_out(
            send_cmd("delta_pop striatum D1_MSN D2_MSN")
        )
        control = send_cmd("control")

        hist["C_gate"].append(gate)
        hist["C_delta"].append(delta)
        hist["C_control"].append(control)

        if step % 50 == 0:
            print(f"[C {step:03d}] relief={gate:.4f} ΔOUT={delta:.6f}")

    # --------------------------------------------------
    # Phase D — Release observation
    # --------------------------------------------------
    print("\n[PHASE D] Control release observation")

    runtime.reset_hypothesis_routing()

    for step in range(200):
        runtime.step()

        gate = parse_gate_relief(send_cmd("gate"))
        delta = parse_delta_out(
            send_cmd("delta_pop striatum D1_MSN D2_MSN")
        )
        control = send_cmd("control")

        hist["D_gate"].append(gate)
        hist["D_delta"].append(delta)
        hist["D_control"].append(control)

        if step % 50 == 0:
            print(f"[D {step:03d}] relief={gate:.4f} ΔOUT={delta:.6f}")

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------
    def mean(xs):
        return sum(xs) / len(xs)

    print("\n=== CONTROL PERSISTENCE & RELEASE SUMMARY ===")

    print("\nBaseline:")
    print(f"Gate mean: {mean(hist['A_gate']):.4f}")
    print(f"ΔOUT mean: {mean(hist['A_delta']):.6f}")

    print("\nPost-commit:")
    print(f"Gate mean: {mean(hist['C_gate']):.4f}")
    print(f"ΔOUT mean: {mean(hist['C_delta']):.6f}")

    print("\nRelease:")
    print(f"Gate mean: {mean(hist['D_gate']):.4f}")
    print(f"ΔOUT mean: {mean(hist['D_delta']):.6f}")

    print("\nManual checks:")
    print("- Control engaged post-commit")
    print("- Suppression present then released")
    print("- Working state disengaged")
    print("- No second decision")
    print("- No ΔOUT rebound")

    print("============================================")


if __name__ == "__main__":
    main()
