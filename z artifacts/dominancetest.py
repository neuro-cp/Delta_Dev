from __future__ import annotations

import socket
import time
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

HOST = "127.0.0.1"
PORT = 5557

LOG_PATH = Path(r"C:\Users\Admin\Desktop\neural framework\runtime_log.txt")

DT = 0.01
HOOK_STEPS = 25
HOOK_WAIT = DT * HOOK_STEPS

BASELINE_WAIT = 6.0
SHORT_WAIT = 1.2
DECAY_WAIT = 4.0

POKE_MAG = 25.0


# ============================================================
# LOGGING
# ============================================================

def log(line: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{ts}] {line}"
    print(msg)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


# ============================================================
# TCP SEND (ONE COMMAND PER CONNECTION)
# ============================================================

def send(cmd: str, expect_reply: bool = True, timeout: float = 3.0) -> str:
    try:
        with socket.create_connection((HOST, PORT), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall((cmd.strip() + "\n").encode("utf-8"))

            if not expect_reply:
                return ""

            try:
                return sock.recv(16384).decode("utf-8", errors="replace").strip()
            except Exception:
                return ""
    except Exception as e:
        return f"ERROR: {e}"


# ============================================================
# SNAPSHOTS
# ============================================================

def snap_region(tag: str, region: str) -> None:
    log(f"[SNAPSHOT] {tag} :: {region}")
    out = send(f"stats {region}")
    log(out if out else "NO DATA")


def snap_context(tag: str) -> None:
    log(f"[CONTEXT] {tag}")
    out = send("ctx")
    log(out if out else "CONTEXT EMPTY")


def snap_striatum(tag: str) -> None:
    log(f"[STRIATUM] {tag}")
    out = send("striatum")
    log(out if out else "NO DATA")


def poke(region: str, mag: float) -> None:
    send(f"poke {region} {mag}", expect_reply=False)
    log(f"[POKE] {region} {mag}")


# ============================================================
# EXPERIMENT — FORCED D1 DOMINANCE
# ============================================================

log("=== BEGIN FORCED STRIATAL DOMINANCE TEST (D1 >> D2) ===")

# ------------------------------------------------------------
# A. BASELINE
# ------------------------------------------------------------

log("[A] Baseline stabilization")
time.sleep(BASELINE_WAIT)

snap_region("baseline", "striatum")
snap_striatum("baseline")

# ------------------------------------------------------------
# B. CONTEXT PRIMING (KEEP ACTIVE)
# ------------------------------------------------------------

log("[B] PFC context priming")
for _ in range(3):
    poke("pfc", POKE_MAG)
    time.sleep(HOOK_WAIT)

snap_context("context_primed")
snap_striatum("context_primed")

# ------------------------------------------------------------
# C. ASYMMETRIC STRIATAL DRIVE (FORCE DECISION)
# ------------------------------------------------------------

log("[C] Forcing D1 dominance")

# Strong repeated excitation to D1
for i in range(6):
    poke("striatum:d1", POKE_MAG * 1.5)
    time.sleep(0.15)

# Weak competing D2 activity (optional but clarifying)
for i in range(2):
    poke("striatum:d2", POKE_MAG * 0.3)
    time.sleep(0.15)

time.sleep(SHORT_WAIT)

snap_region("forced_d1", "striatum")
snap_striatum("forced_d1")
snap_region("forced_d1", "gpi")

# ------------------------------------------------------------
# D. HOLD PHASE (SEE IF DOMINANCE PERSISTS)
# ------------------------------------------------------------

log("[D] Holding dominance (no input)")
time.sleep(DECAY_WAIT)

snap_striatum("hold")
snap_region("hold", "gpi")

# ------------------------------------------------------------
# E. RELEASE / RECOVERY
# ------------------------------------------------------------

log("[E] Recovery phase")
time.sleep(DECAY_WAIT)

snap_striatum("recovery")
snap_region("recovery", "gpi")

log("=== FORCED DOMINANCE TEST COMPLETE ===")
