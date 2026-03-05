# engine/tests/test_md_stimulus_trace.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


BASE_DIR = Path(__file__).resolve().parents[2]
OUT_DIR = BASE_DIR / "logs"
OUT_DIR.mkdir(exist_ok=True, parents=True)


# ============================================================
# CONFIG
# ============================================================

@dataclass(frozen=True)
class RunConfig:
    dt: float = 0.01

    # total timeline
    warmup_steps: int = 200
    stim_steps: int = 120
    post_steps: int = 400

    # stimulation target
    stim_region: str = "md"
    stim_population: str = "RELAY_CELLS"
    stim_magnitude: float = 0.040  # adjust as needed (keep modest)

    # what to watch (these lines will match your zlog parser format)
    watch_pairs: Tuple[Tuple[str, str], ...] = (
        ("md", "RELAY_CELLS"),
        ("trn", "INTERNEURONS"),
    )

    # how chatty should stdout be?
    print_every: int = 25          # print compact “population view” every N steps
    table_every: int = 100         # try printing a wider view every N steps (best effort)

    # files
    zlog_name: str = "zlog_MD_STIM.txt"      # simple line log (parser-friendly)
    trace_name: str = "trace_MD_STIM.jsonl"  # richer JSONL trace


CFG = RunConfig()


# ============================================================
# INTROSPECTION HELPERS (robust to small API differences)
# ============================================================

def _maybe_call(obj: Any, name: str, *args: Any, **kwargs: Any) -> Tuple[bool, Any]:
    fn = getattr(obj, name, None)
    if callable(fn):
        try:
            return True, fn(*args, **kwargs)
        except TypeError:
            return False, None
    return False, None


def get_gate_relief(rt: BrainRuntime) -> Optional[float]:
    ok, s = _maybe_call(rt, "snapshot_gate_state")
    if ok and isinstance(s, dict) and "relief" in s:
        try:
            return float(s["relief"])
        except Exception:
            return None
    return None


def get_dominance_delta(rt: BrainRuntime) -> Optional[float]:
    # Try common snapshots first
    for name in ("snapshot_striatum_state", "snapshot_dominance", "snapshot_competition_state"):
        ok, s = _maybe_call(rt, name)
        if ok and isinstance(s, dict):
            for k in ("delta", "dominance_delta", "delta_dominance"):
                if k in s:
                    try:
                        return float(s[k])
                    except Exception:
                        pass

    # Try digging through the CompetitionKernel if exposed
    ck = getattr(rt, "competition_kernel", None)
    if ck is not None:
        ok, s = _maybe_call(ck, "snapshot")
        if ok and isinstance(s, dict):
            for k in ("delta", "dominance_delta", "delta_dominance"):
                if k in s:
                    try:
                        return float(s[k])
                    except Exception:
                        pass
    return None


def get_decision_state(rt: BrainRuntime) -> Dict[str, Any]:
    # Canonical snapshot if present
    ok, s = _maybe_call(rt, "snapshot_decision_state")
    if ok and isinstance(s, dict):
        return s

    # Sometimes decision latch is exposed directly
    latch = getattr(rt, "decision_latch", None)
    if latch is not None:
        ok, s = _maybe_call(latch, "snapshot")
        if ok and isinstance(s, dict):
            return s

    # Worst case: attempt common attrs
    out: Dict[str, Any] = {}
    for attr in ("decision_made", "decision_winner", "committed"):
        if hasattr(rt, attr):
            out[attr] = getattr(rt, attr)
    return out


def get_control_state(rt: BrainRuntime) -> Dict[str, Any]:
    ok, s = _maybe_call(rt, "snapshot_control_state")
    if ok and isinstance(s, dict):
        return s
    hook = getattr(rt, "control_hook", None)
    if hook is not None:
        ok, s = _maybe_call(hook, "snapshot")
        if ok and isinstance(s, dict):
            return s
    return {}


def get_working_state(rt: BrainRuntime) -> Dict[str, Any]:
    ok, s = _maybe_call(rt, "snapshot_working_state")
    if ok and isinstance(s, dict):
        return s
    wk = getattr(rt, "working_state", None)
    if wk is not None:
        ok, s = _maybe_call(wk, "snapshot")
        if ok and isinstance(s, dict):
            return s
    return {}


def get_value_state(rt: BrainRuntime) -> Dict[str, Any]:
    # common: flags on runtime
    out: Dict[str, Any] = {}
    for k in ("enable_vta_value", "vta_value_mag"):
        if hasattr(rt, k):
            out[k] = getattr(rt, k)
    # adapter snapshot if present
    adapter = getattr(rt, "vta_value_adapter", None)
    if adapter is not None:
        ok, s = _maybe_call(adapter, "snapshot")
        if ok and isinstance(s, dict):
            out.update({"adapter": s})
    return out


def get_urgency_state(rt: BrainRuntime) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k in ("enable_urgency",):
        if hasattr(rt, k):
            out[k] = getattr(rt, k)
    sig = getattr(rt, "urgency_signal", None)
    if sig is not None:
        out.update(
            enabled=getattr(sig, "enabled", None),
            value=getattr(sig, "value", None),
            rise_rate=getattr(sig, "rise_rate", None),
            decay_rate=getattr(sig, "decay_rate", None),
        )
    adapter = getattr(rt, "urgency_adapter", None)
    if adapter is not None:
        ok, s = _maybe_call(adapter, "snapshot")
        if ok and isinstance(s, dict):
            out["adapter"] = s
    return out


def get_population_activity(rt: BrainRuntime, region: str, population: str) -> Optional[float]:
    """
    Best-effort way to get a single population activity scalar.
    This is intentionally defensive so the test survives small refactors.
    """

    # 1) Dedicated snapshot method (if you have it)
    for name in ("snapshot_population_activity", "get_population_activity"):
        ok, v = _maybe_call(rt, name, region, population)
        if ok:
            try:
                return float(v)
            except Exception:
                pass

    # 2) Snapshot of all populations
    for name in ("snapshot_populations", "snapshot_population_table", "snapshot_population_view"):
        ok, s = _maybe_call(rt, name)
        if ok and isinstance(s, dict):
            # common shapes:
            # s[region][population] = activity
            # s[region][population] = {"activity": x, ...}
            try:
                r = s.get(region) or s.get(region.lower()) or s.get(region.upper())
                if isinstance(r, dict):
                    p = r.get(population) or r.get(population.lower()) or r.get(population.upper())
                    if isinstance(p, dict):
                        for k in ("activity", "value", "rate"):
                            if k in p:
                                return float(p[k])
                    if p is not None:
                        return float(p)
            except Exception:
                pass

    # 3) Direct brain structure access (last resort)
    brain = getattr(rt, "brain", None)
    if isinstance(brain, dict):
        r = brain.get(region) or brain.get(region.lower()) or brain.get(region.upper())
        if r is not None:
            pops = getattr(r, "populations", None)
            if isinstance(pops, dict):
                p = pops.get(population) or pops.get(population.lower()) or pops.get(population.upper())
                if p is not None:
                    for attr in ("activity", "value", "rate", "output", "state"):
                        if hasattr(p, attr):
                            try:
                                return float(getattr(p, attr))
                            except Exception:
                                pass
    return None


def print_compact_population_view(rt: BrainRuntime, step: int) -> None:
    # A “population view” that doesn’t require TCP mode switching.
    parts = [f"[STEP {step:04d}]"]
    for (r, p) in CFG.watch_pairs:
        v = get_population_activity(rt, r, p)
        parts.append(f"{r}.{p}={v:.6f}" if v is not None else f"{r}.{p}=None")

    relief = get_gate_relief(rt)
    delta = get_dominance_delta(rt)
    d = get_decision_state(rt)

    if delta is not None:
        parts.append(f"delta={delta:.6f}")
    if relief is not None:
        parts.append(f"relief={relief:.4f}")

    # decision fields vary; pull the common ones without assuming schema
    committed = d.get("committed", d.get("decision_made", d.get("made", False)))
    winner = d.get("winner", d.get("decision_winner", d.get("channel")))
    parts.append(f"committed={bool(committed)}")
    parts.append(f"winner={winner}")

    print(" | ".join(parts))


def print_wide_view_best_effort(rt: BrainRuntime, step: int) -> None:
    # If your runtime has a pretty “population table” printer, use it.
    for name in ("print_population_table", "print_populations", "dump_populations"):
        ok, _ = _maybe_call(rt, name)
        if ok:
            print(f"\n--- POPULATION TABLE @ step {step} ---")
            _maybe_call(rt, name)
            print("--- END TABLE ---\n")
            return
    # Otherwise: do nothing (best effort).


# ============================================================
# MAIN TEST
# ============================================================

def main() -> None:
    zlog_path = OUT_DIR / CFG.zlog_name
    trace_path = OUT_DIR / CFG.trace_name

    loader = NeuralFrameworkLoader(BASE_DIR)
    loader.load_neuron_bases()
    loader.load_regions()
    brain = loader.compile()

    rt = BrainRuntime(brain=brain, dt=CFG.dt)

    total_steps = CFG.warmup_steps + CFG.stim_steps + CFG.post_steps
    stim_start = CFG.warmup_steps
    stim_end = CFG.warmup_steps + CFG.stim_steps  # exclusive

    print(f"[RUN] total_steps={total_steps} (warmup={CFG.warmup_steps}, stim={CFG.stim_steps}, post={CFG.post_steps})")
    print(f"[STIM] {CFG.stim_region}.{CFG.stim_population} magnitude={CFG.stim_magnitude} steps=[{stim_start}, {stim_end})")
    print(f"[OUT] zlog={zlog_path}")
    print(f"[OUT] trace={trace_path}\n")

    # Line log: keep it compatible with your existing parser:
    #   "^md  RELAY_CELLS  <step>  <value>"
    with zlog_path.open("w", encoding="utf-8") as fz, trace_path.open("w", encoding="utf-8") as fj:
        for step in range(total_steps):

            # Apply stimulus during stim window (no TCP interaction needed)
            if stim_start <= step < stim_end:
                rt.inject_stimulus(
                    region_id=CFG.stim_region,
                    population_id=CFG.stim_population,
                    magnitude=CFG.stim_magnitude,
                )

            rt.step()

            # --- zlog lines (parser-friendly) ---
            for (r, p) in CFG.watch_pairs:
                v = get_population_activity(rt, r, p)
                if v is None:
                    # Keep file structure consistent even if a read fails
                    v = float("nan")
                fz.write(f"{r} {p} {step} {v:.8f}\n")

            # --- rich JSONL trace (for “why is it doing that?” moments) ---
            relief = get_gate_relief(rt)
            delta = get_dominance_delta(rt)
            decision = get_decision_state(rt)
            control = get_control_state(rt)
            working = get_working_state(rt)
            value = get_value_state(rt)
            urgency = get_urgency_state(rt)

            record: Dict[str, Any] = {
                "step": step,
                "t_runtime": float(getattr(rt, "t", step * CFG.dt)),
                "phase": (
                    "warmup" if step < stim_start else
                    "stim" if step < stim_end else
                    "post"
                ),
                "watch": {
                    f"{r}.{p}": get_population_activity(rt, r, p)
                    for (r, p) in CFG.watch_pairs
                },
                "gate_relief": relief,
                "dominance_delta": delta,
                "decision": decision,
                "control": control,
                "working": working,
                "value": value,
                "urgency": urgency,
            }
            fj.write(json.dumps(record) + "\n")

            # --- stdout “population view” without any mode switching ---
            if (step % CFG.print_every) == 0:
                print_compact_population_view(rt, step)

            if CFG.table_every > 0 and (step % CFG.table_every) == 0 and step != 0:
                print_wide_view_best_effort(rt, step)

    print("\n[DONE] Logs written.")
    print(f"  - {zlog_path}")
    print(f"  - {trace_path}")


if __name__ == "__main__":
    # Run from project root:
    #   python -m engine.tests.test_md_stimulus_trace
    main()
