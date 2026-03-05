import socket
import time
from pathlib import Path
from typing import Iterable, Sequence


# ============================================================
# CONFIG
# ============================================================

HOST = "127.0.0.1"
PORT = 5557

LOG_PATH = Path(r"C:\Users\Admin\Desktop\neural framework\runtime_log.txt")

DT = 0.01  # must match BrainRuntime(dt=0.01) in test_runtime/testing harness

BASELINE_STEPS = 300        # ~3s @ dt=0.01
SHORT_DELAY = 150           # ~1.5s
RECOVERY_DELAY = 400        # ~4s

POKE_MAG = 25.0
TOP_N = 5

# For BG→GPi→MD gating semantics (current milestone)
REGIONS: Sequence[str] = ("striatum", "gpi", "md", "pfc")


# ============================================================
# SOCKET HELPERS
# ============================================================

def _send(cmd: str) -> str:
    """
    Send a single command and return the reply (best effort).
    """
    with socket.create_connection((HOST, PORT), timeout=3) as sock:
        sock.sendall((cmd.strip() + "\n").encode("utf-8"))
        sock.settimeout(2.0)
        try:
            return sock.recv(4096).decode("utf-8", errors="replace").strip()
        except Exception:
            return ""


# ============================================================
# LOGGING
# ============================================================

def log(line: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{ts}] {line}"
    print(msg)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def snapshot(label: str, regions: Iterable[str]) -> None:
    log(f"[SNAPSHOT] {label}")

    # New: semantic observability
    gate = _send("gate")
    if gate:
        for ln in gate.splitlines():
            log(f"[GATE] {ln}")

    stri = _send("striatum")
    if stri:
        for ln in stri.splitlines():
            log(f"[STRI] {ln}")

    ctx = _send("ctx")
    if ctx:
        for ln in ctx.splitlines():
            log(f"[CTX] {ln}")

    # Per-region stats + tops
    for r in regions:
        stats = _send(f"stats {r}")
        if stats:
            log(f"[STATS] {stats}")

        top = _send(f"top {r} {TOP_N}")
        if top:
            log(f"[TOP] {r} :: {top}")


def poke(region: str, mag: float) -> None:
    rep = _send(f"poke {region} {mag}")
    log(f"[POKE] {region} {mag} :: {rep or 'OK'}")


def wait_steps(n: int) -> None:
    # runtime runs independently; we just wait wall time
    time.sleep(n * DT)


# ============================================================
# EXPERIMENT
# ============================================================

log("=== BEGIN BG→GPi→MD GATING PROBE ===")

# ------------------------------------------------------------
# A. BASELINE
# ------------------------------------------------------------
log("[A] Baseline stabilization")
wait_steps(BASELINE_STEPS)
snapshot("baseline", REGIONS)

# ------------------------------------------------------------
# B. STRIATUM DRIVE (force a decision pressure)
# ------------------------------------------------------------
log("[B] Striatum excitation (decision pressure)")
poke("striatum", POKE_MAG)

wait_steps(SHORT_DELAY)
snapshot("post_striatum_short", REGIONS)

wait_steps(RECOVERY_DELAY)
snapshot("post_striatum_recovery", REGIONS)

# ------------------------------------------------------------
# C. GPi PULSE (should suppress MD if your gate is correct)
# ------------------------------------------------------------
log("[C] GPi inhibitory output pulse (should suppress MD relay)")
poke("gpi", POKE_MAG)

wait_steps(SHORT_DELAY)
snapshot("post_gpi_short", REGIONS)

wait_steps(RECOVERY_DELAY)
snapshot("post_gpi_recovery", REGIONS)

# ------------------------------------------------------------
# D. MD PULSE (sanity check thalamus responds)
# ------------------------------------------------------------
log("[D] MD relay excitation (sanity check)")
poke("md", POKE_MAG)

wait_steps(SHORT_DELAY)
snapshot("post_md_short", REGIONS)

wait_steps(RECOVERY_DELAY)
snapshot("post_md_recovery", REGIONS)

# ------------------------------------------------------------
# END
# ------------------------------------------------------------
log("=== EXPERIMENT COMPLETE ===")
