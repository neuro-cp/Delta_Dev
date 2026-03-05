from __future__ import annotations

import socket
import time
import csv
from pathlib import Path
from typing import Optional

# ============================================================
# CONFIG
# ============================================================

HOST = "127.0.0.1"
PORT = 5557

DT = 0.01
OBS_STEPS = 160
SLEEP_S = DT * 25

BASE_DIR = Path(r"C:\Users\Admin\Desktop\neural framework")
OUT_DIR = BASE_DIR / "engine" / "tests" / "_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LOG_PATH = OUT_DIR / "tcp_post_decision_decay_log.txt"
CSV_PATH = OUT_DIR / "tcp_post_decision_decay.csv"

# ============================================================
# TCP
# ============================================================

def send(cmd: str) -> str:
    try:
        with socket.create_connection((HOST, PORT), timeout=3.0) as sock:
            sock.sendall((cmd.strip() + "\n").encode("utf-8"))
            return sock.recv(65535).decode("utf-8", errors="replace").strip()
    except Exception as e:
        log(f"[TCP ERROR] {cmd} -> {e}")
        return ""

# ============================================================
# LOGGING
# ============================================================

def ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")

def log(msg: str) -> None:
    line = f"[{ts()}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ============================================================
# CSV
# ============================================================

def init_csv() -> None:
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "step",
            "wall_time",
            "control",
            "working",
            "gate",
            "decision",
        ])

def append_csv(step: int, control: str, working: str, gate: str, decision: str):
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            step,
            time.time(),
            control,
            working,
            gate,
            decision,
        ])

# ============================================================
# MAIN
# ============================================================

def main() -> None:
    log("=== BEGIN POST-DECISION DECAY / RELEASE TEST (TCP) ===")
    init_csv()

    # --------------------------------------------------------
    # Phase 0: Baseline
    # --------------------------------------------------------
    log("[PHASE 0] Baseline snapshot")

    log(send("control"))
    log(send("working"))

    # --------------------------------------------------------
    # Phase 1: Lawful forced commit
    # --------------------------------------------------------
    log("[PHASE 1] Forcing lawful decision commit")
    send("force_commit")

    time.sleep(DT * 10)

    log("[POST-COMMIT SNAPSHOT]")
    log(send("control"))
    log(send("working"))
    log(send("decision"))

    # --------------------------------------------------------
    # Phase 2: Observe decay / release
    # --------------------------------------------------------
    log("[PHASE 2] Observing executive decay and release")

    for step in range(OBS_STEPS):
        time.sleep(SLEEP_S)

        control = send("control")
        working = send("working")
        gate = send("gate")
        decision = send("decision")

        if step % 10 == 0:
            log(f"[STEP {step:04d}] control phase snapshot")

        append_csv(
            step=step,
            control=control,
            working=working,
            gate=gate,
            decision=decision,
        )

    # --------------------------------------------------------
    # Done
    # --------------------------------------------------------
    log("=== TEST COMPLETE ===")
    log("Expected outcomes:")
    log("• Control exits post-commit naturally")
    log("• suppress_alternatives returns to false")
    log("• working_state disengages")
    log("• No new decision fires")
    log("• Clean return to pre-decision")
    log(f"Outputs:\n  {CSV_PATH}\n  {LOG_PATH}")

if __name__ == "__main__":
    main()
