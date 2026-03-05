from __future__ import annotations

import csv
import socket
import time
from pathlib import Path
from typing import Optional, Dict


HOST = "127.0.0.1"
PORT = 5557

BASE_DIR = Path(r"C:\Users\Admin\Desktop\neural framework")
OUT_DIR = BASE_DIR / "engine" / "tests" / "_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

STAMP = time.strftime("%Y%m%d_%H%M%S")
OUT_TXT = OUT_DIR / f"tcp_value_ramp_gate_response_{STAMP}.txt"
OUT_CSV = OUT_DIR / f"tcp_value_ramp_gate_response_{STAMP}.csv"

# Respect ValuePolicy.min_interval (0.1s) with margin
STEP_SLEEP_S = 0.12

# How many times to call value_set 0.78 (each allowed call can move +0.1)
RAMP_CALLS = 10

# After ramp, hold observation window (wall-clock)
HOLD_S = 6.0

# After value_clear, observe decay window
DECAY_S = 6.0


def send(cmd: str, timeout: float = 3.0) -> str:
    with socket.create_connection((HOST, PORT), timeout=timeout) as sock:
        sock.sendall((cmd.strip() + "\n").encode("utf-8"))
        return sock.recv(65535).decode("utf-8", errors="replace").strip()


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(OUT_TXT, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def parse_value(s: str) -> Optional[float]:
    # "VALUE: 0.1234"
    if not s.startswith("VALUE:"):
        return None
    try:
        return float(s.split(":", 1)[1].strip())
    except Exception:
        return None


def parse_gate_relief(s: str) -> Optional[float]:
    # gate dump includes lines like: "relief=0.4548"
    for line in s.splitlines():
        line = line.strip()
        if line.startswith("relief="):
            try:
                return float(line.split("=", 1)[1].strip())
            except Exception:
                return None
    return None


def parse_decision_winner(s: str) -> str:
    # decision dump often includes "winner=..." or "winner: ..."
    for line in s.splitlines():
        t = line.strip().lower()
        if t.startswith("winner="):
            return line.split("=", 1)[1].strip()
        if t.startswith("winner:"):
            return line.split(":", 1)[1].strip()
    return "None"


def parse_control_phase(s: str) -> str:
    # CONTROL: { ... "phase": "pre-decision" ... }
    if "phase" not in s:
        return "unknown"
    # keep it simple: just find the phase substring
    idx = s.find('"phase"')
    if idx < 0:
        return "unknown"
    tail = s[idx: idx + 80]
    return tail.replace("\n", " ").strip()


def snapshot(tag: str) -> Dict[str, object]:
    raw_value = send("value")
    raw_gate = send("gate")
    raw_decision = send("decision")
    raw_control = send("control")

    v = parse_value(raw_value)
    relief = parse_gate_relief(raw_gate)
    winner = parse_decision_winner(raw_decision)
    phase = parse_control_phase(raw_control)

    log(f"[{tag}] value={v} gate_relief={relief} decision={winner} control_phase~ {phase}")
    return {
        "t_wall": time.time(),
        "tag": tag,
        "value": v,
        "gate_relief": relief,
        "decision": winner,
        "control_phase": phase,
        "raw_value": raw_value,
        "raw_gate": raw_gate,
        "raw_decision": raw_decision,
        "raw_control": raw_control,
    }


def write_csv_row(row: Dict[str, object]) -> None:
    exists = OUT_CSV.exists()
    with open(OUT_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["t_wall", "tag", "value", "gate_relief", "decision", "control_phase"])
        w.writerow([row["t_wall"], row["tag"], row["value"], row["gate_relief"], row["decision"], row["control_phase"]])


def main() -> None:
    log("=== BEGIN: TCP Value Ramp -> Gate Response -> Decay ===")
    log("[CLEAN] reset_latch + value_clear")
    log("  " + send("reset_latch"))
    log("  " + send("value_clear"))
    time.sleep(STEP_SLEEP_S)

    row = snapshot("baseline")
    write_csv_row(row)

    # ------------------------------------------------------------
    # RAMP: repeatedly ask for 0.78, policy will move in +0.1 steps
    # ------------------------------------------------------------
    log(f"[RAMP] Calling value_set 0.78 x{RAMP_CALLS} (sleep {STEP_SLEEP_S}s each)")
    for i in range(1, RAMP_CALLS + 1):
        out = send("value_set 0.78")
        log(f"  (call {i:02d}) {out}")
        time.sleep(STEP_SLEEP_S)
        row = snapshot(f"ramp_{i:02d}")
        write_csv_row(row)

    # ------------------------------------------------------------
    # HOLD: observe gate response while value signal runs
    # ------------------------------------------------------------
    log(f"[HOLD] observing for {HOLD_S}s (no further value_set)")
    t0 = time.time()
    k = 0
    while (time.time() - t0) < HOLD_S:
        time.sleep(STEP_SLEEP_S)
        k += 1
        row = snapshot(f"hold_{k:02d}")
        write_csv_row(row)

    # ------------------------------------------------------------
    # CLEAR + DECAY OBS
    # ------------------------------------------------------------
    log("[CLEAN] value_clear (then observe decay)")
    log("  " + send("value_clear"))
    time.sleep(STEP_SLEEP_S)

    row = snapshot("after_clear_0")
    write_csv_row(row)

    log(f"[DECAY] observing for {DECAY_S}s")
    t1 = time.time()
    j = 0
    while (time.time() - t1) < DECAY_S:
        time.sleep(STEP_SLEEP_S)
        j += 1
        row = snapshot(f"decay_{j:02d}")
        write_csv_row(row)

    log("=== END ===")
    log(f"Outputs:\n  {OUT_TXT}\n  {OUT_CSV}")


if __name__ == "__main__":
    main()
