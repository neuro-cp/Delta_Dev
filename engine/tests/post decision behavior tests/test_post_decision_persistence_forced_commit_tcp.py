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

LOG_PATH = OUT_DIR / "tcp_forced_commit_log.txt"
CSV_PATH = OUT_DIR / "tcp_forced_commit_post.csv"

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
# PARSING (minimal, robust)
# ============================================================

def parse_control_phase(out: str) -> Optional[str]:
    if not out:
        return None
    for line in out.splitlines():
        if "phase" in line.lower():
            return line.strip()
    return None

def parse_working(out: str) -> str:
    return out.strip() if out else ""

def parse_striatum(out: str) -> str:
    return out.strip() if out else ""

def parse_gate(out: str) -> str:
    return out.strip() if out else ""

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
            "striatum",
            "gate",
        ])

def append_csv(
    step: int,
    control: str,
    working: str,
    striatum: str,
    gate: str,
) -> None:
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            step,
            time.time(),
            control,
            working,
            striatum,
            gate,
        ])

# ============================================================
# MAIN
# ============================================================

def main() -> None:
    log("=== BEGIN FORCED COMMIT POST-DECISION TEST (TCP) ===")
    init_csv()

    # ------------------------------------------------------------
    # Phase 0: Baseline snapshot (pre-commit)
    # ------------------------------------------------------------
    log("[PHASE 0] Baseline snapshot")

    base_control = send("control")
    base_working = send("working")
    base_striatum = send("striatum")
    base_gate = send("gate")

    log("[BASELINE]")
    log(base_control)
    log(base_working)

    # ------------------------------------------------------------
    # Phase 1: Forced decision commit (TEST HARNESS)
    # ------------------------------------------------------------
    log("[PHASE 1] FORCING DECISION COMMIT (test harness)")

    # This command must already exist in your server for testing.
    # It should:
    #   - set latch committed = True
    #   - select existing dominant channel
    #   - NOT modify salience/value/inputs
    send("force_commit", expect_reply=False)

    time.sleep(DT * 10)

    post_control = send("control")
    post_working = send("working")

    log("[POST-COMMIT SNAPSHOT]")
    log(post_control)
    log(post_working)

    # ------------------------------------------------------------
    # Phase 2: Post-decision persistence (NO STIMULUS)
    # ------------------------------------------------------------
    log("[PHASE 2] Post-decision persistence (no stimulus)")

    for step in range(POST_STEPS):
        time.sleep(POST_SLEEP_S)

        control = send("control")
        working = send("working")
        striatum = send("striatum")
        gate = send("gate")

        if step % 10 == 0:
            log(
                f"[POST {step:04d}] "
                f"control={parse_control_phase(control)}"
            )

        append_csv(
            step=step,
            control=control,
            working=working,
            striatum=striatum,
            gate=gate,
        )

    # ------------------------------------------------------------
    # Done
    # ------------------------------------------------------------
    log("=== TEST COMPLETE ===")
    log("Expectations:")
    log("• Control enters post-commit immediately")
    log("• Working state engages")
    log("• No re-decision")
    log("• Dominance persists then decays")
    log("• Clean recovery, no hysteresis")
    log(f"Outputs:\n  {CSV_PATH}\n  {LOG_PATH}")

if __name__ == "__main__":
    main()
