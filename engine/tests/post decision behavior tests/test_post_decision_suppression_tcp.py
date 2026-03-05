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
POST_STEPS = 120
POST_SLEEP_S = DT * 25

BASE_DIR = Path(r"C:\Users\Admin\Desktop\neural framework")
OUT_DIR = BASE_DIR / "engine" / "tests" / "_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LOG_PATH = OUT_DIR / "tcp_post_decision_suppression_log.txt"
CSV_PATH = OUT_DIR / "tcp_post_decision_suppression.csv"

# ============================================================
# TCP
# ============================================================

def send(cmd: str, expect_reply: bool = True) -> str:
    try:
        with socket.create_connection((HOST, PORT), timeout=3.0) as sock:
            sock.sendall((cmd.strip() + "\n").encode("utf-8"))
            if not expect_reply:
                return ""
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
            "decision",
            "gate",
        ])

def append_csv(step: int, control: str, working: str, decision: str, gate: str) -> None:
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            step,
            time.time(),
            control,
            working,
            decision,
            gate,
        ])

# ============================================================
# MAIN
# ============================================================

def main() -> None:
    log("=== BEGIN POST-DECISION SUPPRESSION TEST (TCP) ===")
    init_csv()

    # ------------------------------------------------------------
    # Phase 0: Baseline
    # ------------------------------------------------------------
    log("[PHASE 0] Baseline snapshot")

    log(send("control"))
    log(send("working"))

    # ------------------------------------------------------------
    # Phase 1: Force lawful commit
    # ------------------------------------------------------------
    log("[PHASE 1] Forcing lawful decision commit")

    send("force_commit", expect_reply=False)
    time.sleep(DT * 10)

    control = send("control")
    working = send("working")
    decision = send("decision")

    log("[POST-COMMIT SNAPSHOT]")
    log(control)
    log(working)
    log(decision)

    # ------------------------------------------------------------
    # Phase 2: Apply competing input AFTER commit
    # ------------------------------------------------------------
    log("[PHASE 2] Applying competing inputs (should be suppressed)")

    # Region-level competing poke
    send("poke association_cortex 0.05", expect_reply=False)

    # Salience poke (competing assembly; arbitrary label)
    send("salience_set competing 1.0", expect_reply=False)

    # Optional value poke (should NOT cause re-decision)
    send("value_set 0.8", expect_reply=False)

    # ------------------------------------------------------------
    # Phase 3: Observe suppression
    # ------------------------------------------------------------
    log("[PHASE 3] Observing suppression dynamics")

    for step in range(POST_STEPS):
        time.sleep(POST_SLEEP_S)

        control = send("control")
        working = send("working")
        decision = send("decision")
        gate = send("gate")

        if step % 10 == 0:
            log(f"[POST {step:04d}] control={control.splitlines()[0]}")

        append_csv(
            step=step,
            control=control,
            working=working,
            decision=decision,
            gate=gate,
        )

    # ------------------------------------------------------------
    # Done
    # ------------------------------------------------------------
    log("=== TEST COMPLETE ===")
    log("Expected:")
    log("• No new decision fired")
    log("• No phase regression")
    log("• Suppress_alternatives remains true")
    log("• Working state persists then decays")
    log("• Clean executive dominance")
    log(f"Outputs:\n  {CSV_PATH}\n  {LOG_PATH}")

if __name__ == "__main__":
    main()
