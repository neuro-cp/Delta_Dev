# salience_testing.py  (Suite 4)
# Place this file in: C:\Users\Admin\Desktop\neural framework\salience_testing.py
#
# Purpose:
#   Suite 4 = control-surface characterization (no architecture changes).
#   We keep runtime + latch + salience as-is, and sweep *operating conditions*.
#
# Outputs (modpanda schema LOCKED):
#   - dominance_trace.csv
#   - decision_latch_trace.csv
#   - decision_debug_trace.csv
# Plus a timestamped console log:
#   - salience_suite4_<RUN>.txt
#
from __future__ import annotations

import sys
import csv
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List, Tuple

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime
from engine.command_server import start_command_server

# Salience engine (observation-driven; writes ONLY to runtime.salience field)
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
PRINT_EVERY = 100

# Suite pacing
BASELINE_STEPS = 500
COOLDOWN_STEPS = 350

SHORT = 160
MED = 320
LONG = 700

# Conservative magnitudes (we’re not “forcing,” we’re probing)
POKE_TINY = 0.12
POKE_SMALL = 0.25
POKE_MED = 0.45
POKE_BIG = 0.85

# Striatum population keys (region JSON keys)
STR_D1 = "D1_MSN"
STR_D2 = "D2_MSN"

# Cortex targets
C_PFC = ("pfc", None)
C_ASSOC = ("association_cortex", None)
C_S1 = ("s1", None)

BASE_RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
CURRENT_RUN_ID = BASE_RUN_ID


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

    dom = snap.get("dominance", {}) or {}
    d1 = float(dom.get("D1", 0.0))
    d2 = float(dom.get("D2", 0.0))
    delta = d1 - d2

    step = int(runtime.step_count)
    t = float(runtime.time)
    winner = snap.get("winner")
    relief = float(gate["relief"])

    with open(DOM_CSV, "a", newline="") as f:
        csv.writer(f).writerow([CURRENT_RUN_ID, step, winner, d1, d2, delta])

    with open(DEBUG_CSV, "a", newline="") as f:
        csv.writer(f).writerow([CURRENT_RUN_ID, step, t, winner, d1, d2, delta, relief])

    if gate.get("decision"):
        d = gate["decision"]
        with open(DECISION_CSV, "a", newline="") as f:
            csv.writer(f).writerow([CURRENT_RUN_ID, step, t, d["winner"], d["delta_dominance"], d["relief"]])


# ============================================================
# RUN-ID SCOPING (so modpanda can filter runs)
# ============================================================

class RunScope:
    def __init__(self, run_id: str):
        self.new = run_id
        self.old = None

    def __enter__(self):
        global CURRENT_RUN_ID
        self.old = CURRENT_RUN_ID
        CURRENT_RUN_ID = self.new

    def __exit__(self, exc_type, exc, tb):
        global CURRENT_RUN_ID
        CURRENT_RUN_ID = self.old if self.old is not None else BASE_RUN_ID


# ============================================================
# STIM HELPERS (test-only; no runtime edits)
# ============================================================

def poke_region(runtime: BrainRuntime, region: str, pop: Optional[str], mag: float) -> None:
    runtime.inject_stimulus(region, pop, None, mag)


def poke_striatum(runtime: BrainRuntime, which: str, mag: float) -> None:
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
# PARAM SNAPSHOT / RESTORE (no drift across subtests)
# ============================================================

def snapshot_runtime_knobs(runtime: BrainRuntime) -> Dict[str, Any]:
    snap: Dict[str, Any] = {}

    # GPi gating knobs
    snap["gpi_gain"] = getattr(runtime, "gpi_gain", None)
    snap["gpi_floor"] = getattr(runtime, "gpi_floor", None)

    # Context knobs
    snap["ctx_decay_tau"] = getattr(getattr(runtime, "context", None), "decay_tau", None)

    # PFC hook knobs
    pfc_hook = getattr(runtime, "pfc_context", None)
    snap["pfc_thr"] = getattr(pfc_hook, "activity_threshold", None)
    snap["pfc_gain"] = getattr(pfc_hook, "injection_gain", None)
    snap["pfc_max"] = getattr(pfc_hook, "max_inject_per_step", None)
    snap["pfc_to_global"] = getattr(pfc_hook, "inject_to_global", None)

    # Salience knobs
    sal = getattr(runtime, "salience", None)
    snap["sal_decay_tau"] = getattr(sal, "decay_tau", None)
    snap["sal_max_value"] = getattr(sal, "max_value", None)

    return snap


def restore_runtime_knobs(runtime: BrainRuntime, snap: Dict[str, Any]) -> None:
    if snap.get("gpi_gain") is not None:
        runtime.gpi_gain = float(snap["gpi_gain"])
    if snap.get("gpi_floor") is not None:
        runtime.gpi_floor = float(snap["gpi_floor"])

    ctx = getattr(runtime, "context", None)
    if ctx is not None and snap.get("ctx_decay_tau") is not None:
        ctx.decay_tau = float(snap["ctx_decay_tau"])

    pfc_hook = getattr(runtime, "pfc_context", None)
    if pfc_hook is not None:
        if snap.get("pfc_thr") is not None:
            pfc_hook.activity_threshold = float(snap["pfc_thr"])
        if snap.get("pfc_gain") is not None:
            pfc_hook.injection_gain = float(snap["pfc_gain"])
        # max_inject_per_step may be None
        pfc_hook.max_inject_per_step = snap.get("pfc_max")
        if snap.get("pfc_to_global") is not None:
            pfc_hook.inject_to_global = bool(snap["pfc_to_global"])

    sal = getattr(runtime, "salience", None)
    if sal is not None:
        if snap.get("sal_decay_tau") is not None:
            sal.decay_tau = float(snap["sal_decay_tau"])
        if snap.get("sal_max_value") is not None:
            sal.max_value = float(snap["sal_max_value"])


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
    start_step = int(runtime.step_count)

    for i in range(int(steps)):
        if on_step is not None:
            on_step(i)

        runtime.step()

        # Salience driven ONLY by observations
        if getattr(runtime, "enable_salience", True):
            try:
                sal_engine.step(runtime, runtime.salience)
            except Exception:
                pass

        log_step(runtime)

        if (int(runtime.step_count) - start_step) % int(print_every) == 0:
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


def cooldown(runtime: BrainRuntime, sal_engine: SalienceEngine, steps: int, label: str) -> None:
    run_block(runtime=runtime, sal_engine=sal_engine, steps=steps, label=label, on_step=None)


# ============================================================
# SUITE 4: CONTROL-SURFACE CHARACTERIZATION
# ============================================================

# -----------------------------
# 4A — Urgency compression
# -----------------------------

def suite4A_urgency_compression(runtime: BrainRuntime, sal_engine: SalienceEngine) -> None:
    """
    We tighten/loosen gating (GPi relief landscape) and replay the SAME packet.
    Goal: show earlier/later commitment propensity without changing latch.
    """
    base_snap = snapshot_runtime_knobs(runtime)

    # Same stimulus packet each time (timing > magnitude)
    def packet_factory(d1_mag: float) -> StepFn:
        def on_step(i: int) -> None:
            if i == 10:
                poke_region(runtime, C_S1[0], C_S1[1], POKE_MED)
            if i == 13:
                poke_region(runtime, C_PFC[0], C_PFC[1], POKE_SMALL)
            if i == 16:
                poke_striatum(runtime, STR_D1, d1_mag)
        return on_step

    # Three gate regimes: more strict -> baseline -> more permissive
    regimes = [
        ("strict", 0.70, 0.22),
        ("baseline", float(getattr(runtime, "gpi_gain", 0.6)), float(getattr(runtime, "gpi_floor", 0.25))),
        ("permissive", 0.50, 0.30),
    ]

    for name, gpi_gain, gpi_floor in regimes:
        restore_runtime_knobs(runtime, base_snap)
        runtime.gpi_gain = float(gpi_gain)
        runtime.gpi_floor = float(gpi_floor)

        with RunScope(f"{BASE_RUN_ID}_S4A_{name}"):
            print(f"\n[S4A] regime={name} gpi_gain={runtime.gpi_gain:.3f} gpi_floor={runtime.gpi_floor:.3f}")
            cooldown(runtime, sal_engine, COOLDOWN_STEPS, f"S4A-{name}: settle")
            run_block(
                runtime=runtime,
                sal_engine=sal_engine,
                steps=LONG,
                label=f"S4A-{name}: same packet replay",
                on_step=packet_factory(d1_mag=POKE_SMALL),
            )
            cooldown(runtime, sal_engine, COOLDOWN_STEPS, f"S4A-{name}: cooldown")

    restore_runtime_knobs(runtime, base_snap)


# -----------------------------
# 4B — Context persistence bias
# -----------------------------

def suite4B_context_persistence(runtime: BrainRuntime, sal_engine: SalienceEngine) -> None:
    """
    Sweep context decay tau (working-memory persistence) and replay same packet.
    Expect: longer tau can prime trajectories (without forcing latch).
    """
    base_snap = snapshot_runtime_knobs(runtime)
    ctx = getattr(runtime, "context", None)
    if ctx is None:
        print("[S4B] Runtime has no context; skipping.")
        return

    taus = [2.5, 5.0, 10.0]  # short / baseline-ish / long
    for tau in taus:
        restore_runtime_knobs(runtime, base_snap)
        ctx.decay_tau = float(tau)

        with RunScope(f"{BASE_RUN_ID}_S4B_tau{tau:g}"):
            print(f"\n[S4B] context.decay_tau={ctx.decay_tau:.3f}")

            # Prime PFC lightly for a while (context injection hook does the writing)
            def prime(i: int) -> None:
                if 10 <= i < 210 and i % 12 == 0:
                    poke_region(runtime, C_PFC[0], C_PFC[1], POKE_SMALL)

            cooldown(runtime, sal_engine, COOLDOWN_STEPS, "S4B: settle")
            run_block(runtime=runtime, sal_engine=sal_engine, steps=MED, label="S4B: prime PFC (context buildup)", on_step=prime)

            # Now play identical coincidence packet (low energy)
            def packet(i: int) -> None:
                if i == 10:
                    poke_region(runtime, C_S1[0], C_S1[1], POKE_MED)
                if i == 13:
                    poke_region(runtime, C_PFC[0], C_PFC[1], POKE_SMALL)
                if i == 16:
                    poke_striatum(runtime, STR_D1, POKE_TINY)

            run_block(runtime=runtime, sal_engine=sal_engine, steps=LONG, label="S4B: packet after priming", on_step=packet)
            cooldown(runtime, sal_engine, COOLDOWN_STEPS, "S4B: cooldown")

    restore_runtime_knobs(runtime, base_snap)


# -----------------------------
# 4C — Salience fatigue proxy (non-learning habituation lookalike)
# -----------------------------

def suite4C_salience_fatigue(runtime: BrainRuntime, sal_engine: SalienceEngine) -> None:
    """
    Repeated identical packets, then a ‘novel’ packet.
    We’re not implementing learning; we’re checking whether the *field dynamics*
    plus sources produce diminishing marginal effect (or not).
    """
    base_snap = snapshot_runtime_knobs(runtime)

    with RunScope(f"{BASE_RUN_ID}_S4C_repeat"):
        cooldown(runtime, sal_engine, COOLDOWN_STEPS, "S4C: settle")

        # Repeated packets
        def repeat_packets(i: int) -> None:
            # every 35 steps, same packet
            if i % 35 == 0 and i < 35 * 18:
                poke_region(runtime, C_S1[0], C_S1[1], POKE_MED)
            if i % 35 == 3 and i < 35 * 18:
                poke_region(runtime, C_PFC[0], C_PFC[1], POKE_SMALL)
            if i % 35 == 6 and i < 35 * 18:
                poke_striatum(runtime, STR_D1, POKE_TINY)

        run_block(runtime=runtime, sal_engine=sal_engine, steps=35 * 20, label="S4C: repeated identical packets", on_step=repeat_packets)
        cooldown(runtime, sal_engine, COOLDOWN_STEPS, "S4C: cooldown")

    with RunScope(f"{BASE_RUN_ID}_S4C_novel"):
        # Novel packet: different ordering + D2 destabilize
        def novel(i: int) -> None:
            if i == 10:
                poke_region(runtime, C_ASSOC[0], C_ASSOC[1], POKE_MED)
            if i == 14:
                poke_striatum(runtime, STR_D2, POKE_TINY)
            if i == 18:
                poke_region(runtime, C_PFC[0], C_PFC[1], POKE_SMALL)

        run_block(runtime=runtime, sal_engine=sal_engine, steps=LONG, label="S4C: novel packet", on_step=novel)
        cooldown(runtime, sal_engine, COOLDOWN_STEPS, "S4C: cooldown")

    restore_runtime_knobs(runtime, base_snap)


# -----------------------------
# 4D — Conflict under constrained gate
# -----------------------------

def suite4D_conflict_constrained_gate(runtime: BrainRuntime, sal_engine: SalienceEngine) -> None:
    """
    Slightly constrain the gate, then run a conflict stream.
    Compare against baseline gate settings inside this suite via separate run_ids.
    """
    base_snap = snapshot_runtime_knobs(runtime)

    def conflict_stream(i: int) -> None:
        if i == 10:
            poke_striatum(runtime, STR_D2, POKE_MED)  # early shove
        # sustained sensory stream
        if 40 <= i < 520 and i % 12 == 0:
            poke_region(runtime, C_S1[0], C_S1[1], POKE_SMALL)
        # intermittent PFC + D1 micro-destabilization
        if 45 <= i < 525 and i % 24 == 0:
            poke_region(runtime, C_PFC[0], C_PFC[1], POKE_SMALL)
            poke_striatum(runtime, STR_D1, POKE_TINY)

    # Baseline gate
    restore_runtime_knobs(runtime, base_snap)
    with RunScope(f"{BASE_RUN_ID}_S4D_gate_baseline"):
        cooldown(runtime, sal_engine, COOLDOWN_STEPS, "S4D-baseline: settle")
        run_block(runtime=runtime, sal_engine=sal_engine, steps=700, label="S4D-baseline: conflict stream", on_step=conflict_stream)
        cooldown(runtime, sal_engine, COOLDOWN_STEPS, "S4D-baseline: cooldown")

    # Constrained gate (a touch stricter)
    restore_runtime_knobs(runtime, base_snap)
    runtime.gpi_gain = float(getattr(runtime, "gpi_gain", 0.6)) + 0.08
    runtime.gpi_floor = max(0.18, float(getattr(runtime, "gpi_floor", 0.25)) - 0.05)

    with RunScope(f"{BASE_RUN_ID}_S4D_gate_constrained"):
        print(f"\n[S4D] constrained gate: gpi_gain={runtime.gpi_gain:.3f} gpi_floor={runtime.gpi_floor:.3f}")
        cooldown(runtime, sal_engine, COOLDOWN_STEPS, "S4D-constrained: settle")
        run_block(runtime=runtime, sal_engine=sal_engine, steps=700, label="S4D-constrained: conflict stream", on_step=conflict_stream)
        cooldown(runtime, sal_engine, COOLDOWN_STEPS, "S4D-constrained: cooldown")

    restore_runtime_knobs(runtime, base_snap)


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    log_path = BASE_DIR / f"salience_suite4_{BASE_RUN_ID}.txt"
    logger = TeeLogger(log_path)
    sys.stdout = logger

    try:
        print("=== SALIENCE + BG SUITE 4 (CONTROL SURFACE) ===\n")
        print(f"Base Run ID: {BASE_RUN_ID}")
        print(f"DT: {DT}")
        print("CSV schema locked for modpanda. Run segments use suffixes in run_id.\n")

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
        # Salience engine
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
        with RunScope(f"{BASE_RUN_ID}_S4_0_baseline"):
            run_block(runtime=runtime, sal_engine=sal_engine, steps=BASELINE_STEPS, label="S4-0: Baseline stabilization", on_step=None)
            cooldown(runtime, sal_engine, COOLDOWN_STEPS, "S4-0: cooldown")

        # ----------------------------------------------------
        # Suite 4 experiments
        # ----------------------------------------------------
        suite4A_urgency_compression(runtime, sal_engine)
        suite4B_context_persistence(runtime, sal_engine)
        suite4C_salience_fatigue(runtime, sal_engine)
        suite4D_conflict_constrained_gate(runtime, sal_engine)

        # ----------------------------------------------------
        # DONE
        # ----------------------------------------------------
        print("\n=== SUITE 4 COMPLETE ===")
        print("Files updated (append-safe):")
        print(" - dominance_trace.csv")
        print(" - decision_latch_trace.csv")
        print(" - decision_debug_trace.csv")
        print(f"Log file: {log_path.name}")
        print("Use modpanda to visualize trajectories (filter by run_id suffixes).")

    finally:
        sys.stdout = logger.stdout
        logger.close()
        print(f"\n[LOG] Full console output saved to: {log_path}")


if __name__ == "__main__":
    main()
