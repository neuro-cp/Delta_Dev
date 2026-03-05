from __future__ import annotations

import sys
import csv
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List, Tuple

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime
from engine.command_server import start_command_server

# Salience (read-only to runtime; we only update the field)
from engine.salience.salience_engine import SalienceEngine
from engine.salience.sources.surprise_source import SurpriseSource
from engine.salience.sources.competition_source import CompetitionSource
from engine.salience.sources.persistence_source import PersistenceSource


# ============================================================
# PATHS (must match modpanda expectations)
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DOM_CSV = BASE_DIR / "dominance_trace.csv"
DECISION_CSV = BASE_DIR / "decision_latch_trace.csv"
DEBUG_CSV = BASE_DIR / "decision_debug_trace.csv"


# ============================================================
# CONFIG
# ============================================================

DT = 0.01

# Print cadence
PRINT_EVERY = 50

# Suite pacing (steps)
BASELINE_STEPS = 400

# “Core” windows used across subtests
SHORT_WINDOW = 120
MED_WINDOW = 250
LONG_WINDOW = 500

# Poke magnitudes (keep conservative; we sweep later)
POKE_TINY = 0.15
POKE_SMALL = 0.35
POKE_MED = 0.60
POKE_BIG = 1.00

# Striatum populations (must match your region JSON keys)
STR_D1 = "D1_MSN"
STR_D2 = "D2_MSN"

# Cortex targets
C_PFC = ("pfc", None)
C_ASSOC = ("association_cortex", None)
C_S1 = ("s1", None)

# Run id (used by modpanda)
RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")


# ============================================================
# STDOUT TEE LOGGER
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
# CSV HELPERS (modpanda schema is LOCKED)
# ============================================================

def _init_csv_if_missing(path: Path, header: List[str]) -> None:
    # Do NOT clobber existing files: lets you accumulate “all data we currently have”
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
# STIM HELPERS (test-only; no runtime edits)
# ============================================================

def poke_region(runtime: BrainRuntime, region: str, pop: Optional[str], mag: float) -> None:
    runtime.inject_stimulus(region, pop, None, mag)


def poke_striatum(runtime: BrainRuntime, which: str, mag: float) -> None:
    # which in {STR_D1, STR_D2}
    runtime.inject_stimulus("striatum", which, None, mag)


def salience_stats(runtime: BrainRuntime) -> Tuple[int, float]:
    try:
        dump = runtime.salience.dump()
        if not dump:
            return 0, 0.0
        return len(dump), max(float(v) for v in dump.values())
    except Exception:
        return 0, 0.0


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
    print_every: int = PRINT_EVERY,
) -> None:
    print(f"\n=== {label} ===")
    start_step = runtime.step_count

    for i in range(steps):
        if on_step is not None:
            on_step(i)

        runtime.step()

        # Drive salience ONLY by observations (no runtime mutation)
        if getattr(runtime, "enable_salience", True):
            try:
                sal_engine.step(runtime, runtime.salience)
            except Exception:
                # fail closed
                pass

        log_step(runtime)

        # Periodic console snapshot
        if (runtime.step_count - start_step) % print_every == 0:
            gate = runtime.snapshot_gate_state()
            k, mx = salience_stats(runtime)
            snap = getattr(runtime, "_last_striatum_snapshot", {}) or {}
            dom = snap.get("dominance", {}) or {}
            d1 = float(dom.get("D1", 0.0))
            d2 = float(dom.get("D2", 0.0))
            delta = d1 - d2

            print(
                f"[step {runtime.step_count:06d}] "
                f"t={gate['time']:.3f} relief={gate['relief']:.3f} "
                f"winner={snap.get('winner')} "
                f"D1={d1:.4f} D2={d2:.4f} Δ={delta:.4f} "
                f"sal_keys={k} max_sal={mx:.4f}"
            )


# ============================================================
# SUITE 2: EXPERIMENTS
# ============================================================

def exp_symmetry_oscillation(runtime: BrainRuntime, sal_engine: SalienceEngine) -> None:
    """
    Alternate D1/D2 pokes equally -> should produce bounded oscillations and no commitment.
    """
    period = 10
    def on_step(i: int) -> None:
        if i % period == 0:
            poke_striatum(runtime, STR_D1, POKE_SMALL)
        if i % period == period // 2:
            poke_striatum(runtime, STR_D2, POKE_SMALL)

    run_block(runtime=runtime, sal_engine=sal_engine, steps=LONG_WINDOW, label="S2-A: Symmetry oscillation (D1<->D2 equal)", on_step=on_step)


def exp_temporal_coincidence(runtime: BrainRuntime, sal_engine: SalienceEngine) -> None:
    """
    Tight timing windows: cortex poke followed by striatum poke (and vice versa).
    We’re looking for structured Δ inflections from timing, not magnitude.
    """
    seq: List[Tuple[int, Callable[[], None]]] = []

    # pattern 1: sensory->PFC->D1 (tight)
    base = 0
    for rep in range(8):
        t0 = base + rep * 40
        seq.append((t0 + 0, lambda r=runtime: poke_region(r, C_S1[0], C_S1[1], POKE_MED)))
        seq.append((t0 + 2, lambda r=runtime: poke_region(r, C_PFC[0], C_PFC[1], POKE_SMALL)))
        seq.append((t0 + 4, lambda r=runtime: poke_striatum(r, STR_D1, POKE_TINY)))

    # pattern 2: D2 destabilize then assoc “meaning” input
    base = 400
    for rep in range(8):
        t0 = base + rep * 45
        seq.append((t0 + 0, lambda r=runtime: poke_striatum(r, STR_D2, POKE_TINY)))
        seq.append((t0 + 3, lambda r=runtime: poke_region(r, C_ASSOC[0], C_ASSOC[1], POKE_MED)))

    schedule: Dict[int, List[Callable[[], None]]] = {}
    for t, fn in seq:
        schedule.setdefault(t, []).append(fn)

    def on_step(i: int) -> None:
        for fn in schedule.get(i, []):
            fn()

    run_block(runtime=runtime, sal_engine=sal_engine, steps=800, label="S2-B: Temporal coincidence windows (timing > magnitude)", on_step=on_step)


def exp_salience_stacking(runtime: BrainRuntime, sal_engine: SalienceEngine) -> None:
    """
    Same total “energy”, different timing.
    Fast pokes (within salience decay window) should stack more than slow pokes.
    """
    # Fast stack: 20 quick pulses
    def on_fast(i: int) -> None:
        if i < 200 and i % 8 == 0:
            poke_region(runtime, "pfc", None, POKE_SMALL)
            poke_striatum(runtime, STR_D1, POKE_TINY)

    run_block(runtime=runtime, sal_engine=sal_engine, steps=MED_WINDOW, label="S2-C1: Fast stacking (within decay window)", on_step=on_fast)

    # Cooldown
    run_block(runtime=runtime, sal_engine=sal_engine, steps=MED_WINDOW, label="S2-C1b: Cooldown", on_step=None)

    # Slow stack: same number of pulses, spaced out
    pulses = 20
    gap = 25  # slower than the fast case
    def on_slow(i: int) -> None:
        if i % gap == 0 and (i // gap) < pulses:
            poke_region(runtime, "pfc", None, POKE_SMALL)
            poke_striatum(runtime, STR_D1, POKE_TINY)

    run_block(runtime=runtime, sal_engine=sal_engine, steps=pulses * gap + 50, label="S2-C2: Slow stacking (leaks through decay)", on_step=on_slow)

    # Cooldown
    run_block(runtime=runtime, sal_engine=sal_engine, steps=MED_WINDOW, label="S2-C2b: Cooldown", on_step=None)


def exp_anti_salience(runtime: BrainRuntime, sal_engine: SalienceEngine) -> None:
    """
    Loud-but-meaningless control:
    Big single poke to cortex, no follow-up, no coincidence.
    Expect: small Δ, no latch.
    """
    def on_step(i: int) -> None:
        if i == 5:
            poke_region(runtime, "association_cortex", None, POKE_BIG)

    run_block(runtime=runtime, sal_engine=sal_engine, steps=LONG_WINDOW, label="S2-D: Loud but meaningless control (should NOT commit)", on_step=on_step)


def exp_channel_conflict(runtime: BrainRuntime, sal_engine: SalienceEngine) -> None:
    """
    Conflict test:
    - Initial D2 shove
    - Then salience-relevant cortical stream aligned to D1 destabilization pulses
    We look for “magnitude wins early, but bias can steer trajectory later.”
    """
    def on_step(i: int) -> None:
        if i == 10:
            poke_striatum(runtime, STR_D2, POKE_MED)  # shove
        # sustained “meaning” stream
        if 40 <= i < 340 and i % 12 == 0:
            poke_region(runtime, "s1", None, POKE_SMALL)
        if 45 <= i < 345 and i % 24 == 0:
            poke_region(runtime, "pfc", None, POKE_SMALL)
            poke_striatum(runtime, STR_D1, POKE_TINY)  # light D1 destabilization

    run_block(runtime=runtime, sal_engine=sal_engine, steps=500, label="S2-E: Conflict (D2 shove vs D1-biased stream)", on_step=on_step)


def exp_magnitude_sweep(runtime: BrainRuntime, sal_engine: SalienceEngine) -> None:
    """
    Small sweep over D1/D2 poke magnitudes to map sensitivity.
    This should NOT require any schema changes; it’s all in the trace.
    """
    mags = [POKE_TINY, POKE_SMALL, POKE_MED]
    block = 220

    for m in mags:
        def on_step(i: int, mag=m) -> None:
            # paired: D1 destabilize + sensory coincidence
            if i == 5:
                poke_striatum(runtime, STR_D1, mag)
            if i == 7:
                poke_region(runtime, "s1", None, POKE_SMALL)
            if i == 9:
                poke_region(runtime, "pfc", None, POKE_SMALL)

        run_block(runtime=runtime, sal_engine=sal_engine, steps=block, label=f"S2-F: Magnitude sweep (D1 destabilize mag={m:.2f})", on_step=on_step)
        run_block(runtime=runtime, sal_engine=sal_engine, steps=180, label="S2-Fb: Cooldown", on_step=None)

    for m in mags:
        def on_step(i: int, mag=m) -> None:
            # paired: D2 destabilize + sensory coincidence
            if i == 5:
                poke_striatum(runtime, STR_D2, mag)
            if i == 7:
                poke_region(runtime, "s1", None, POKE_SMALL)
            if i == 9:
                poke_region(runtime, "pfc", None, POKE_SMALL)

        run_block(runtime=runtime, sal_engine=sal_engine, steps=block, label=f"S2-G: Magnitude sweep (D2 destabilize mag={m:.2f})", on_step=on_step)
        run_block(runtime=runtime, sal_engine=sal_engine, steps=180, label="S2-Gb: Cooldown", on_step=None)


def exp_decision_attempt(runtime: BrainRuntime, sal_engine: SalienceEngine) -> None:
    """
    Optional “try to elicit commitment” without changing architecture:
    Use repeated coincidence + light D1 bias.
    Commitment may still be rare (good).
    """
    def on_step(i: int) -> None:
        # repeated coincidence packets
        if i % 30 == 0 and i < 900:
            poke_region(runtime, "s1", None, POKE_MED)
        if i % 30 == 3 and i < 900:
            poke_region(runtime, "pfc", None, POKE_MED)
        if i % 30 == 6 and i < 900:
            poke_striatum(runtime, STR_D1, POKE_SMALL)

    run_block(runtime=runtime, sal_engine=sal_engine, steps=1000, label="S2-H: Decision attempt (repeated coincidence packets)", on_step=on_step)
    run_block(runtime=runtime, sal_engine=sal_engine, steps=400, label="S2-Hb: Cooldown", on_step=None)


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    log_path = BASE_DIR / f"salience_testing_{RUN_ID}.txt"
    logger = TeeLogger(log_path)
    sys.stdout = logger

    try:
        print("=== SALIENCE + BG SUITE 2 (FULL) ===\n")
        print(f"Run ID: {RUN_ID}")
        print(f"DT: {DT}")
        print("CSV schema locked for modpanda.\n")

        init_csvs()

        # ----------------------------------------------------
        # Load brain
        # ----------------------------------------------------
        loader = NeuralFrameworkLoader(BASE_DIR)
        loader.load_neuron_bases()
        loader.load_regions()
        loader.load_profiles()

        brain = loader.compile(
            expression_profile="minimal",
            state_profile="awake",
            compound_profile="experimental",
        )

        # ----------------------------------------------------
        # Runtime
        # ----------------------------------------------------
        runtime = BrainRuntime(brain, dt=DT)
        start_command_server(runtime)

        # ----------------------------------------------------
        # Salience engine (drives runtime.salience only)
        # ----------------------------------------------------
        sal_engine = SalienceEngine(
            sources=[
                SurpriseSource(),
                CompetitionSource(),
                PersistenceSource(),
            ]
        )

        print("[OK] Runtime ready")
        print("[OK] Command server running")
        print("[OK] Salience engine online (observation-driven)\n")

        # ----------------------------------------------------
        # 0. Baseline
        # ----------------------------------------------------
        run_block(runtime=runtime, sal_engine=sal_engine, steps=BASELINE_STEPS, label="S2-0: Baseline stabilization")

        # ----------------------------------------------------
        # Suite 2 experiments
        # ----------------------------------------------------
        exp_symmetry_oscillation(runtime, sal_engine)
        exp_temporal_coincidence(runtime, sal_engine)
        exp_salience_stacking(runtime, sal_engine)
        exp_anti_salience(runtime, sal_engine)
        exp_channel_conflict(runtime, sal_engine)
        exp_magnitude_sweep(runtime, sal_engine)
        exp_decision_attempt(runtime, sal_engine)

        # ----------------------------------------------------
        # DONE
        # ----------------------------------------------------
        print("\n=== SUITE 2 COMPLETE ===")
        print("Files updated (append-safe):")
        print(" - dominance_trace.csv")
        print(" - decision_latch_trace.csv")
        print(" - decision_debug_trace.csv")
        print("Use modpanda to visualize trajectories (all runs).")

    finally:
        sys.stdout = logger.stdout
        logger.close()
        print(f"\n[LOG] Full console output saved to: {log_path}")


if __name__ == "__main__":
    main()
