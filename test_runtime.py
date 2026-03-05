# test_runtime.py
# Interactive runtime + TCP command server (instrumentation-only)
#
# Goals:
# - Run BrainRuntime continuously (deterministic-ish wallclock pacing)
# - Provide local keyboard commands (read-only + poke)
# - Expose TCP command server on 5557 (for your external probe scripts)
#
# Notes:
# - This file does NOT modify engine behavior; it only inspects + injects stimuli.
# - Keeps UI lightweight to avoid stutters.

from __future__ import annotations

import time
import os
import sys
import math
from pathlib import Path
from typing import Optional, List, Tuple, Dict

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime
from engine.command_server import start_command_server


# ============================================================
# PLATFORM INPUT HANDLING
# ============================================================

IS_WINDOWS = os.name == "nt"

if IS_WINDOWS:
    import msvcrt
else:
    import select
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_term_settings = termios.tcgetattr(fd)
    tty.setcbreak(fd)


def key_available() -> bool:
    if IS_WINDOWS:
        return msvcrt.kbhit()
    return bool(select.select([sys.stdin], [], [], 0)[0])


def read_key() -> str:
    if IS_WINDOWS:
        return msvcrt.getwch()
    return sys.stdin.read(1)


# ============================================================
# UI CONFIG
# ============================================================

VIEW_MODE = "populations"   # regions | populations | assemblies
SHOW_ZERO = False
UI_INTERVAL = 0.10          # seconds of sim-time between UI refreshes


# ============================================================
# STATS HELPERS
# ============================================================

def _basic_stats(values: List[float]):
    if not values:
        return None
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return mean, math.sqrt(var)


def region_stats(runtime: BrainRuntime, region_id: str) -> Optional[Dict[str, float]]:
    region = runtime.region_states.get(region_id)
    if not region:
        return None

    acts: List[float] = []
    outs: List[float] = []

    for plist in region.get("populations", {}).values():
        for pop in plist:
            acts.append(float(getattr(pop, "activity", 0.0)))
            outs.append(float(pop.output()))

    if not acts:
        return None

    mean, std = _basic_stats(acts)
    return {
        "mass": float(sum(outs)),
        "mean": float(mean),
        "std": float(std),
        "n": float(len(acts)),
    }


def population_stats(runtime: BrainRuntime) -> List[Tuple[str, str, int, float, float]]:
    """
    Returns rows:
      (region_id, population_name, num_assemblies, mass(sum outputs), mean(activity))
    """
    rows: List[Tuple[str, str, int, float, float]] = []

    for rid, region in runtime.region_states.items():
        pops = region.get("populations", {}) or {}
        for pop_name, plist in pops.items():
            acts = [float(getattr(p, "activity", 0.0)) for p in plist]
            outs = [float(p.output()) for p in plist]

            if not acts and not SHOW_ZERO:
                continue

            if not acts:
                rows.append((rid, pop_name, 0, 0.0, 0.0))
                continue

            mean, _ = _basic_stats(acts)
            rows.append((rid, pop_name, len(plist), float(sum(outs)), float(mean)))

    return rows


def assembly_rows(
    runtime: BrainRuntime,
    region_filter: Optional[str] = None,
) -> List[Tuple[str, float, float, str]]:
    """
    Returns rows:
      (assembly_id, activity, output, region_id)
    """
    rows: List[Tuple[str, float, float, str]] = []
    for rid, region in runtime.region_states.items():
        if region_filter and rid != region_filter:
            continue
        pops = region.get("populations", {}) or {}
        for plist in pops.values():
            for pop in plist:
                rows.append((
                    str(getattr(pop, "assembly_id", "")),
                    float(getattr(pop, "activity", 0.0)),
                    float(pop.output()),
                    rid,
                ))
    return rows


def top_assemblies(runtime: BrainRuntime, region: str, n: int = 10) -> List[Tuple[str, float]]:
    rows = assembly_rows(runtime, region)
    rows.sort(key=lambda x: x[2], reverse=True)
    return [(aid, out) for aid, _, out, _ in rows[: max(0, int(n))]]


# ============================================================
# COMMAND HANDLING (READ-ONLY + POKE)
# ============================================================

HELP_TEXT = (
    "Commands:\n"
    "  poke <region|all> <mag>\n"
    "  view regions | populations | assemblies\n"
    "  toggle zeros\n"
    "  stats <region>\n"
    "  top <region> <n>\n"
    "  dump <region>\n"
    "  context\n"
    "  help"
)


def apply_command(runtime: BrainRuntime, cmd: str) -> str:
    global VIEW_MODE, SHOW_ZERO

    cmd = cmd.strip()
    if not cmd:
        return "."

    print(f"\n>>> CMD | t={runtime.time:.3f}s | step={runtime.step_count} | {cmd}")

    parts = cmd.split()
    head = parts[0].lower()

    # ----------------------------
    # HELP
    # ----------------------------
    if head == "help":
        return HELP_TEXT

    # ----------------------------
    # POKE
    # ----------------------------
    if head == "poke":
        if len(parts) != 3:
            return "Usage: poke <region|all> <mag>"
        target = parts[1].lower()
        try:
            mag = float(parts[2])
        except Exception:
            return "ERROR: magnitude must be a float"

        if target == "all":
            for r in runtime.region_states.keys():
                runtime.inject_stimulus(r, magnitude=mag)
            return f"POKE all += {mag}"

        runtime.inject_stimulus(parts[1], magnitude=mag)
        return f"POKE {parts[1]} += {mag}"

    # ----------------------------
    # VIEW
    # ----------------------------
    if head == "view":
        if len(parts) != 2:
            return "Usage: view regions|populations|assemblies"
        mode = parts[1].lower()
        if mode in ("regions", "populations", "assemblies"):
            VIEW_MODE = mode
            return f"View -> {VIEW_MODE.upper()}"
        return "Invalid view. Use: regions | populations | assemblies"

    # ----------------------------
    # TOGGLE
    # ----------------------------
    if head == "toggle":
        if len(parts) != 2:
            return "Usage: toggle zeros"
        if parts[1].lower() != "zeros":
            return "Usage: toggle zeros"
        SHOW_ZERO = not SHOW_ZERO
        return f"Show zeros -> {SHOW_ZERO}"

    # ----------------------------
    # STATS
    # ----------------------------
    if head == "stats":
        if len(parts) != 2:
            return "Usage: stats <region>"
        s = region_stats(runtime, parts[1])
        if not s:
            return "No data."
        return (
            f"{parts[1]} "
            f"MASS={s['mass']:.4f} "
            f"MEAN={s['mean']:.4f} "
            f"STD={s['std']:.4f} "
            f"N={int(s['n'])}"
        )

    # ----------------------------
    # TOP
    # ----------------------------
    if head == "top":
        if len(parts) < 2:
            return "Usage: top <region> <n>"
        region = parts[1]
        try:
            n = int(parts[2]) if len(parts) >= 3 else 10
        except Exception:
            n = 10

        rows = top_assemblies(runtime, region, n)
        if not rows:
            return "No assemblies."
        return "\n".join(f"{aid} :: {val:.4f}" for aid, val in rows)

    # ----------------------------
    # DUMP
    # ----------------------------
    if head == "dump":
        if len(parts) != 2:
            return "Usage: dump <region>"
        rows = assembly_rows(runtime, parts[1])
        print("\nASSEMBLIES:")
        for aid, act, out, _ in rows:
            print(f"{aid:55} {act:10.6f} {out:10.6f}")
        return f"Dumped {len(rows)} assemblies."

    # ----------------------------
    # CONTEXT
    # ----------------------------
    if head == "context":
        ctx = getattr(runtime, "context", None)
        if ctx is None:
            return "CONTEXT: disabled (runtime.context not present)"
        return ctx.stats()

    return "Unknown command. Type 'help'."


# ============================================================
# LOAD + RUN
# ============================================================

# Resolve repository root dynamically (portable across OSes)
ROOT = Path(__file__).resolve().parent

loader = NeuralFrameworkLoader(ROOT)
loader.load_neuron_bases()
loader.load_regions()
loader.load_profiles()

brain = loader.compile(
    expression_profile="human_default",
    state_profile="awake",
    compound_profile="experimental",
)

runtime = BrainRuntime(brain, dt=0.01)

# ============================================================
# STRUCTURAL SALIENCE SPARSITY (EPISODE-LEVEL)
# ============================================================

from engine.salience.salience_sparsity_gate import SalienceSparsityGate

# Collect all assembly IDs known to the runtime
assembly_ids = [
    p.assembly_id
    for p in runtime._all_pops
    if getattr(p, "assembly_id", None) is not None
]

# Create deterministic sparsity gate
sparsity_gate = SalienceSparsityGate(
    keep_ratio=0.25,   # 25% of assemblies eligible
    seed=42,           # deterministic per episode
)

# Initialize eligibility
sparsity_gate.initialize(assembly_ids)

# Attach gate to salience field
runtime.salience.attach_sparsity_gate(sparsity_gate)

print(
    "[INIT] Salience sparsity gate attached:",
    sparsity_gate.stats(),
)


# ------------------------------------------------------------------
# CSV TRACE DE-CONFLICT (IMPORTANT)
# ------------------------------------------------------------------
# CompetitionKernel writes a detailed per-channel trace by default.
# Your external probe script (testingpoke.py) writes a *different schema*
# to dominance_trace.csv. If both point at the same file, it will look like
# "corruption" but it's really two incompatible writers.
#
# We avoid that by giving the kernel trace its own filename.
try:
    runtime.competition_kernel.TRACE_PATH = root / "kernel_dominance_trace.csv"
except Exception:
    # If the kernel object or attribute ever changes, we fail safe:
    # command server must still run.
    pass

# Attach local command handler (keyboard UI)
runtime.apply_command = lambda c: apply_command(runtime, c)  # type: ignore[attr-defined]

# Start TCP server (external scripts)
start_command_server(runtime)

print("\nLIVE RUNTIME | TCP + Keyboard")
print("Port 5557 | Ctrl+C to quit")
print("Default view: POPULATIONS")
print("Type 'help' then Enter for commands.")
print("-" * 110)


# ============================================================
# MAIN LOOP
# ============================================================

next_ui = UI_INTERVAL
t0 = time.perf_counter()
cmd_buffer = ""
last_msg = "Ready."

try:
    while True:
        runtime.step()

        # Keyboard input (non-blocking)
        while key_available():
            ch = read_key()

            if ch in ("\n", "\r"):
                if cmd_buffer.strip():
                    last_msg = apply_command(runtime, cmd_buffer)
                cmd_buffer = ""

            elif ch in ("\b", "\x7f"):
                cmd_buffer = cmd_buffer[:-1]

            elif ch == "\x03":  # Ctrl+C
                raise KeyboardInterrupt

            elif ch.isprintable():
                cmd_buffer += ch

        # UI refresh (based on SIM time, not wall time)
        if runtime.time >= next_ui:
            next_ui += UI_INTERVAL

            print("\n" + "-" * 110)
            print(f"t={runtime.time:.2f}s | view={VIEW_MODE} | zeros={SHOW_ZERO}")

            if VIEW_MODE == "regions":
                print(f"{'REGION':20} {'MASS':>10} {'MEAN':>10} {'STD':>10} {'N':>6}")
                for rid in runtime.region_states.keys():
                    s = region_stats(runtime, rid)
                    if not s and not SHOW_ZERO:
                        continue
                    if not s:
                        print(f"{rid:20} {0:10.4f} {0:10.4f} {0:10.4f} {0:6}")
                    else:
                        print(
                            f"{rid:20} "
                            f"{s['mass']:10.4f} "
                            f"{s['mean']:10.4f} "
                            f"{s['std']:10.4f} "
                            f"{int(s['n']):6d}"
                        )

            elif VIEW_MODE == "populations":
                print(f"{'REGION':15} {'POPULATION':25} {'ASM':>5} {'MASS':>10} {'MEAN':>10}")
                for rid, pop, n, mass, mean in population_stats(runtime):
                    print(f"{rid:15} {pop:25} {n:5d} {mass:10.4f} {mean:10.4f}")

            elif VIEW_MODE == "assemblies":
                # Compact: show top assemblies globally by output
                rows = assembly_rows(runtime)
                rows.sort(key=lambda x: x[2], reverse=True)
                top = rows[:25]
                print(f"{'ASSEMBLY_ID':55} {'ACT':>10} {'OUT':>10} {'REGION':>15}")
                for aid, act, out, rid in top:
                    if (out == 0.0 and not SHOW_ZERO):
                        continue
                    print(f"{aid:55} {act:10.6f} {out:10.6f} {rid:>15}")

            print("-" * 110)
            print(f"last: {last_msg}")
            print(f"> {cmd_buffer}", end="", flush=True)

        # Wallclock pacing: try to keep sim time ~= real time
        elapsed = time.perf_counter() - t0
        if runtime.time > elapsed:
            time.sleep(runtime.time - elapsed)

except KeyboardInterrupt:
    print("\nStopped.")

finally:
    if not IS_WINDOWS:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_term_settings)
