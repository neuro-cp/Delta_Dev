from __future__ import annotations

import sys
import csv
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List, Tuple

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime
from engine.command_server import start_command_server

# Salience (observation-driven only)
from engine.salience.salience_engine import SalienceEngine
from engine.salience.sources.surprise_source import SurpriseSource
from engine.salience.sources.competition_source import CompetitionSource
from engine.salience.sources.persistence_source import PersistenceSource


# ============================================================
# PATHS (LOCKED BY MODPANDA)
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DOM_CSV = BASE_DIR / "dominance_trace.csv"
DECISION_CSV = BASE_DIR / "decision_latch_trace.csv"
DEBUG_CSV = BASE_DIR / "decision_debug_trace.csv"


# ============================================================
# CONFIG
# ============================================================

DT = 0.01
PRINT_EVERY = 50

# Core windows
BASELINE_STEPS = 500
SHORT = 120
MED = 300
LONG = 700

# Magnitudes (intentionally conservative)
POKE_EPS = 0.05
POKE_TINY = 0.15
POKE_SMALL = 0.35
POKE_MED = 0.60
POKE_BIG = 1.00

# Striatum population keys
STR_D1 = "D1_MSN"
STR_D2 = "D2_MSN"

# Cortical regions
C_PFC = ("pfc", None)
C_ASSOC = ("association_cortex", None)
C_S1 = ("s1", None)

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")


# ============================================================
# STDOUT TEE
# ============================================================

class TeeLogger:
    def __init__(self, path: Path):
        self.file = open(path, "w", encoding="utf-8")
        self.stdout = sys.stdout

    def write(self, msg: str) -> None:
        if msg.strip():
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.file.write(f"[{ts}] {msg}")
        else:
            self.file.write(msg)
        self.file.flush()
        self.stdout.write(msg)

    def flush(self) -> None:
        self.file.flush()
        self.stdout.flush()

    def close(self) -> None:
        self.file.close()


# ============================================================
# CSV HELPERS (APPEND-SAFE)
# ============================================================

def _init_csv_if_missing(path: Path, header: List[str]) -> None:
    if path.exists() and path.stat().st_size > 0:
        return
    with open(path, "w", newline="") as f:
        csv.writer(f).writerow(header)


def init_csvs() -> None:
    _init_csv_if_missing(DOM_CSV, ["run_id", "step", "winner", "D1", "D2", "delta"])
    _init_csv_if_missing(DECISION_CSV, ["run_id", "step", "time", "winner", "delta_dominance", "relief"])
    _init_csv_if_missing(DEBUG_CSV, ["run_id", "step", "time", "winner", "D1", "D2", "delta", "relief"])


def log_step(runtime: BrainRuntime) -> None:
    snap = getattr(runtime, "_last_striatum_snapshot", None)
    gate = runtime.snapshot_gate_state()
    if not snap:
        return

    dom = snap.get("dominance", {})
    d1 = float(dom.get("D1", 0.0))
    d2 = float(dom.get("D2", 0.0))
    delta = d1 - d2

    step = int(runtime.step_count)
    t = float(runtime.time)
    winner = snap.get("winner")
    relief = float(gate["relief"])

    with open(DOM_CSV, "a", newline="") as f:
        csv.writer(f).writerow([RUN_ID, step, winner, d1, d2, delta])

    with open(DEBUG_CSV, "a", newline="") as f:
        csv.writer(f).writerow([RUN_ID, step, t, winner, d1, d2, delta, relief])

    if gate.get("decision"):
        d = gate["decision"]
        with open(DECISION_CSV, "a", newline="") as f:
            csv.writer(f).writerow([RUN_ID, step, t, d["winner"], d["delta_dominance"], d["relief"]])


# ============================================================
# STIM HELPERS
# ============================================================

def poke_region(runtime: BrainRuntime, region: str, pop: Optional[str], mag: float) -> None:
    runtime.inject_stimulus(region, pop, None, mag)

def poke_striatum(runtime: BrainRuntime, which: str, mag: float) -> None:
    runtime.inject_stimulus("striatum", which, None, mag)


# ============================================================
# STEPPING HARNESS
# ============================================================

StepFn = Callable[[int], None]

def run_block(
    *,
    runtime: BrainRuntime,
    sal_engine: SalienceEngine,
    steps: int,
    label: str,
    on_step: Optional[StepFn] = None,
) -> None:
    print(f"\n=== {label} ===")
    start = runtime.step_count

    for i in range(steps):
        if on_step:
            on_step(i)

        runtime.step()

        # salience driven only by observation
        sal_engine.step(runtime, runtime.salience)

        log_step(runtime)

        if (runtime.step_count - start) % PRINT_EVERY == 0:
            snap = getattr(runtime, "_last_striatum_snapshot", {}) or {}
            dom = snap.get("dominance", {}) or {}
            d1 = float(dom.get("D1", 0.0))
            d2 = float(dom.get("D2", 0.0))
            delta = d1 - d2
            gate = runtime.snapshot_gate_state()

            print(
                f"[step {runtime.step_count:06d}] "
                f"relief={gate['relief']:.3f} "
                f"winner={snap.get('winner')} "
                f"D1={d1:.4f} D2={d2:.4f} Δ={delta:.4f}"
            )


# ============================================================
# SUITE 3 EXPERIMENTS
# ============================================================

def s3_sensitivity(runtime, sal):
    mags = [POKE_EPS, POKE_TINY, POKE_SMALL]
    for m in mags:
        def on(i, mag=m):
            if i == 5:
                poke_striatum(runtime, STR_D1, mag)
            if i == 8:
                poke_region(runtime, "s1", None, POKE_TINY)
        run_block(runtime=runtime, sal_engine=sal, steps=MED, label=f"S3-A: Sensitivity D1 mag={m}", on_step=on)
        run_block(runtime=runtime, sal_engine=sal, steps=SHORT, label="Cooldown")


def s3_hysteresis(runtime, sal):
    # ramp up
    def up(i):
        if i % 40 == 0 and i < 400:
            poke_striatum(runtime, STR_D1, POKE_TINY)
    run_block(runtime=runtime, sal_engine=sal, steps=500, label="S3-B1: Ramp UP", on_step=up)

    # ramp down
    def down(i):
        if i % 40 == 0 and i < 400:
            poke_striatum(runtime, STR_D2, POKE_TINY)
    run_block(runtime=runtime, sal_engine=sal, steps=500, label="S3-B2: Ramp DOWN", on_step=down)


def s3_salience_saturation(runtime, sal):
    def on(i):
        if i < 200 and i % 6 == 0:
            poke_region(runtime, "pfc", None, POKE_SMALL)
            poke_region(runtime, "s1", None, POKE_SMALL)
    run_block(runtime=runtime, sal_engine=sal, steps=LONG, label="S3-C: Salience saturation burst", on_step=on)
    run_block(runtime=runtime, sal_engine=sal, steps=MED, label="Cooldown")


def s3_delayed_causality(runtime, sal):
    schedule = {
        10: lambda: poke_region(runtime, "s1", None, POKE_MED),
        40: lambda: poke_region(runtime, "pfc", None, POKE_MED),
        90: lambda: poke_striatum(runtime, STR_D1, POKE_TINY),
    }
    def on(i):
        if i in schedule:
            schedule[i]()
    run_block(runtime=runtime, sal_engine=sal, steps=300, label="S3-D: Delayed causality chain", on_step=on)


def s3_near_latch(runtime, sal):
    def on(i):
        if i % 25 == 0:
            poke_region(runtime, "pfc", None, POKE_SMALL)
        if i % 50 == 5:
            poke_striatum(runtime, STR_D1, POKE_TINY)
    run_block(runtime=runtime, sal_engine=sal, steps=900, label="S3-E: Near-latch grazing", on_step=on)


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    log_path = BASE_DIR / f"salience_suite3_{RUN_ID}.txt"
    logger = TeeLogger(log_path)
    sys.stdout = logger

    try:
        print("=== SALIENCE + BG — SUITE 3 ===\n")
        print(f"Run ID: {RUN_ID}\n")

        init_csvs()

        loader = NeuralFrameworkLoader(BASE_DIR)
        loader.load_neuron_bases()
        loader.load_regions()
        loader.load_profiles()

        brain = loader.compile(
            expression_profile="minimal",
            state_profile="awake",
            compound_profile="experimental",
        )

        runtime = BrainRuntime(brain, dt=DT)
        start_command_server(runtime)

        sal = SalienceEngine(
            sources=[SurpriseSource(), CompetitionSource(), PersistenceSource()]
        )

        print("[OK] Runtime + Salience engine ready\n")

        run_block(runtime=runtime, sal_engine=sal, steps=BASELINE_STEPS, label="S3-0: Baseline")

        s3_sensitivity(runtime, sal)
        s3_hysteresis(runtime, sal)
        s3_salience_saturation(runtime, sal)
        s3_delayed_causality(runtime, sal)
        s3_near_latch(runtime, sal)

        print("\n=== SUITE 3 COMPLETE ===")

    finally:
        sys.stdout = logger.stdout
        logger.close()
        print(f"\n[LOG] Saved to {log_path}")


if __name__ == "__main__":
    main()
