from __future__ import annotations

import socket
import time
import json
import re
from pathlib import Path
from typing import Optional, Dict, Tuple

# ============================================================
# CONFIG
# ============================================================

HOST = "127.0.0.1"
PORT = 5557

BASE_DIR = Path(r"C:\Users\Admin\Desktop\neural framework")
OUT_JSON = BASE_DIR / "decision_details.log.jsonl"

DT = 0.01
POLL_TICKS = 25
POLL_SLEEP = DT * POLL_TICKS

FORCED_STEPS = 100

SMALL_POKE = 1.0
ASYM_POKE = 1.0
GATE_OPEN_THRESHOLD = 0.47
#0.47
# ============================================================
# EXPERIMENT (EXPLICIT)
# ============================================================

EXPERIMENT = {
    "suite": "Decision latch validation",
    "test_id": "3/4",
    "name": "Gate-triggered forced decision",
    "description": (
        "Continuously drive striatum at low magnitude. "
        "When gate relief first exceeds threshold, inject "
        "a one-time asymmetry into D1_MSN. "
        "Verify that decision occurs only after gate opening."
    ),
    "parameters": {
        "forced_steps": FORCED_STEPS,
        "baseline_poke": SMALL_POKE,
        "asymmetry_poke": ASYM_POKE,
        "gate_threshold": GATE_OPEN_THRESHOLD,
    },
}

# ============================================================
# TCP
# ============================================================

def send(cmd: str, expect_reply: bool = True) -> str:
    with socket.create_connection((HOST, PORT), timeout=3.0) as sock:
        sock.sendall((cmd.strip() + "\n").encode("utf-8"))
        if not expect_reply:
            return ""
        return sock.recv(65535).decode("utf-8", errors="replace").strip()

def wait_for_server() -> None:
    while True:
        try:
            if "Commands:" in send("help"):
                return
        except Exception:
            pass
        time.sleep(0.5)

# ============================================================
# PARSING
# ============================================================

NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"

def parse_gate(raw: str) -> Optional[float]:
    if not raw:
        return None
    m = re.search(rf"relief\s*=\s*({NUM})", raw)
    return float(m.group(1)) if m else None

def parse_striatum(raw: str) -> Optional[Tuple[str, float, float, float]]:
    if not raw:
        return None

    try:
        winner = re.search(r"winner\s*=\s*(\w+)", raw, re.I).group(1)
        d1 = float(re.search(rf"D1\s*=\s*({NUM})", raw).group(1))
        d2 = float(re.search(rf"D2\s*=\s*({NUM})", raw).group(1))
        t = float(re.search(rf"t\s*=\s*({NUM})", raw).group(1))
        return winner, d1, d2, t
    except Exception:
        return None

def parse_decision(raw: str) -> Optional[Dict]:
    if not raw.startswith("DECISION:"):
        return None

    fields = {}
    for line in raw.splitlines():
        if "=" in line:
            k, v = line.strip().split("=", 1)
            fields[k.strip()] = v.strip()

    required = {"time", "step", "winner", "delta_dominance", "relief"}
    if not required.issubset(fields):
        return None

    return {
        "time": float(fields["time"]),
        "step": int(fields["step"]),
        "winner": fields["winner"],
        "delta_dominance": float(fields["delta_dominance"]),
        "relief": float(fields["relief"]),
    }

def parse_control(raw: str) -> Dict:
    payload = raw.split("CONTROL:", 1)[-1].strip()
    return json.loads(payload)

# ============================================================
# MAIN — TEST 3/4
# ============================================================

def main() -> None:
    print("=== TEST 3/4 — Gate-triggered forced win ===")

    wait_for_server()
    send("reset_latch")

    run_id = 1
    trial = 1
    step = 0

    max_delta = 0.0
    max_relief = 0.0
    decision_seen = False
    gate_opened = False

    for _ in range(FORCED_STEPS):

        # Baseline striatum drive
        send(f"poke striatum {SMALL_POKE}", expect_reply=False)
        time.sleep(POLL_SLEEP)

        gate = parse_gate(send("gate"))
        parsed = parse_striatum(send("striatum"))
        if not parsed:
            step += 1
            continue

        winner, d1, d2, t = parsed
        delta = abs(d1 - d2)

        max_delta = max(max_delta, delta)
        if gate is not None:
            max_relief = max(max_relief, gate)

        # Edge-triggered gate opening
        if gate is not None and gate >= GATE_OPEN_THRESHOLD and not gate_opened:
            gate_opened = True
            send(f"poke striatum:D1_MSN {ASYM_POKE}", expect_reply=False)

        dec_raw = send("decision")
        decision = parse_decision(dec_raw)

        if decision:
            record = {
                "experiment": EXPERIMENT,
                "run_id": run_id,
                "trial": trial,
                "test_step": step,
                "test_time": t,
                "decision": decision,
                "control": parse_control(send("control")),
                "striatum": {
                    "winner": winner,
                    "dominance": {"D2": d2, "D1": d1},
                    "time": t,
                },
                "gate": {
                    "time": t,
                    "relief": gate,
                    "decision": True,
                },
            }

            with open(OUT_JSON, "a", encoding="utf-8") as f:
                json.dump(record, f, indent=2)
                f.write("\n\n")

            print("[OK] Decision logged (TEST 3/4)")
            break

        step += 1

    print("=== SUITE COMPLETE ===")

if __name__ == "__main__":
    main()
