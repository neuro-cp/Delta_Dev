from __future__ import annotations

import json
import socket
import threading
from typing import List, Optional, Tuple, Dict, Any


# ============================================================
# Helpers
# ============================================================

def _basic_stats(values: List[float]) -> Optional[Tuple[float, float]]:
    if not values:
        return None
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return mean, var ** 0.5

def _reset_hypotheses(runtime) -> str:
    if not hasattr(runtime, "reset_hypothesis_routing"):
        return "ERROR: hypothesis reset not supported"

    runtime.reset_hypothesis_routing()
    return "OK hypotheses reset"



def _resolve_region(runtime, region_label: str) -> str:
    if hasattr(runtime, "_resolve_region_key"):
        rk = runtime._resolve_region_key(region_label)
        if rk:
            return rk
    return region_label


def _get_salience(runtime):
    return getattr(runtime, "salience", None)

def _dump_control(runtime) -> str:
    if not hasattr(runtime, "get_control_state"):
        return "CONTROL: unsupported"

    state = runtime.get_control_state()
    if not state:
        return "CONTROL: none"

    if hasattr(state, "to_dict"):
        return "CONTROL:\n" + json.dumps(state.to_dict(), indent=2)

    return f"CONTROL: {state}"



# ============================================================
# Region diagnostics
# ============================================================

def _region_stats(runtime, region_label: str) -> str:
    region_id = _resolve_region(runtime, region_label)

    if hasattr(runtime, "snapshot_region_stats"):
        snap = runtime.snapshot_region_stats(region_id)
        if snap is None:
            return f"ERROR: unknown region '{region_label}' (resolved='{region_id}')"

        return (
            f"{snap['region']} "
            f"MASS={snap['mass']:.4f} "
            f"MEAN={snap['mean']:.4f} "
            f"STD={snap['std']:.4f} "
            f"N={snap['n']}"
        )

    # Fallback (legacy runtime)
    region = runtime.region_states.get(region_id)
    if not region:
        return f"ERROR: unknown region '{region_label}' (resolved='{region_id}')"

    acts, outs = [], []
    for plist in region["populations"].values():
        for pop in plist:
            acts.append(float(getattr(pop, "activity", 0.0)))
            outs.append(float(pop.output()))

    if not acts:
        return f"{region_id} MASS=0.0000 MEAN=0.0000 STD=0.0000 N=0"

    mean, std = _basic_stats(acts)
    return (
        f"{region_id} "
        f"MASS={sum(outs):.4f} "
        f"MEAN={mean:.4f} "
        f"STD={std:.4f} "
        f"N={len(acts)}"
    )

def _population_stats(runtime, region_label: str, population_label: str) -> str:
    region_id = _resolve_region(runtime, region_label)
    region = runtime.region_states.get(region_id)
    if not region:
        return f"ERROR: unknown region '{region_label}' (resolved='{region_id}')"

    pops = region.get("populations", {})
    if population_label not in pops:
        return f"ERROR: unknown population '{population_label}' in region '{region_id}'"

    acts: List[float] = []
    outs: List[float] = []

    for pop in pops[population_label]:
        acts.append(float(getattr(pop, "activity", 0.0)))
        outs.append(float(pop.output()))

    if not acts:
        return (
            f"{region_id}:{population_label} "
            f"MASS=0.0000 MEAN=0.0000 STD=0.0000 N=0"
        )

    mean, std = _basic_stats(acts)
    return (
        f"{region_id}:{population_label} "
        f"MASS={sum(outs):.4f} "
        f"MEAN={mean:.4f} "
        f"STD={std:.4f} "
        f"N={len(acts)}"
    )

def _delta_population(
    runtime,
    region_label: str,
    pop_a: str,
    pop_b: str,
) -> str:
    region_id = _resolve_region(runtime, region_label)
    region = runtime.region_states.get(region_id)
    if not region:
        return f"ERROR: unknown region '{region_label}' (resolved='{region_id}')"

    pops = region.get("populations", {})

    if pop_a not in pops:
        return f"ERROR: unknown population '{pop_a}' in region '{region_id}'"
    if pop_b not in pops:
        return f"ERROR: unknown population '{pop_b}' in region '{region_id}'"

    def _collect(pop_list):
        acts, outs = [], []
        for p in pop_list:
            acts.append(float(getattr(p, "activity", 0.0)))
            outs.append(float(p.output()))
        return acts, outs

    acts_a, outs_a = _collect(pops[pop_a])
    acts_b, outs_b = _collect(pops[pop_b])

    if not acts_a or not acts_b:
        return (
            f"{region_id}:{pop_a} vs {pop_b} "
            f"ΔACT=0.000000 ΔOUT=0.000000 "
            f"N_A={len(acts_a)} N_B={len(acts_b)}"
        )

    mean_act_a = sum(acts_a) / len(acts_a)
    mean_act_b = sum(acts_b) / len(acts_b)

    mean_out_a = sum(outs_a) / len(outs_a)
    mean_out_b = sum(outs_b) / len(outs_b)

    return (
        f"{region_id}:{pop_a} vs {pop_b} "
        f"ΔACT={abs(mean_act_a - mean_act_b):.6f} "
        f"ΔOUT={abs(mean_out_a - mean_out_b):.6f} "
        f"N_A={len(acts_a)} "
        f"N_B={len(acts_b)}"
    )


def _top_assemblies(runtime, region_label: str, n: int) -> str:
    region_id = _resolve_region(runtime, region_label)
    region = runtime.region_states.get(region_id)
    if not region:
        return f"ERROR: unknown region '{region_label}'"

    rows = []
    for plist in region["populations"].values():
        for pop in plist:
            rows.append((pop.assembly_id, float(pop.output())))

    if not rows:
        return "EMPTY"

    rows.sort(key=lambda x: x[1], reverse=True)
    return " | ".join(
        f"{aid} :: {val:.4f}" for aid, val in rows[: max(1, n)]
    )

def _dump_assemblies_json(runtime, region_label: str) -> str:
    """
    Inspection-only.
    Writes per-assembly activity/output to a JSON file.
    """
    region_id = _resolve_region(runtime, region_label)
    region = runtime.region_states.get(region_id)
    if not region:
        return f"ERROR: unknown region '{region_label}' (resolved='{region_id}')"

    assemblies = []
    for pop_label, plist in region.get("populations", {}).items():
        for pop in plist:
            assemblies.append({
                "assembly_id": pop.assembly_id,
                "population": pop_label,
                "activity": float(getattr(pop, "activity", 0.0)),
                "output": float(pop.output()),
            })

    payload = {
        "region": region_id,
        "step": getattr(runtime, "step_count", None),
        "time": getattr(runtime, "time", None),
        "assemblies": assemblies,
    }

    filename = f"assembly_dump_{region_id}_{payload['step']}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return f"OK wrote {len(assemblies)} assemblies to {filename}"

# ============================================================
# Context diagnostics
# ============================================================

def _dump_context(runtime) -> str:
    ctx = getattr(runtime, "context", None)
    if not ctx:
        return "CONTEXT: unavailable"

    dump = ctx.dump()
    if not dump:
        return "CONTEXT EMPTY"

    return "\n".join(
        f"{k}: {v}" for k, v in dump.items()
    )


def _dump_context_full(runtime) -> str:
    ctx = getattr(runtime, "context", None)
    if not ctx:
        return "CONTEXT: unavailable"
    return str(ctx.stats())


# ============================================================
# Salience diagnostics
# ============================================================

def _dump_salience(runtime) -> str:
    sal = _get_salience(runtime)
    if not sal:
        return "SALIENCE: not enabled"

    stats = sal.stats()
    if not stats:
        return "SALIENCE EMPTY"

    return (
        "SALIENCE:\n"
        f"  count={stats.get('count', 0)}\n"
        f"  mean={stats.get('mean', 0.0):.4f}\n"
        f"  max={stats.get('max', 0.0):.4f}"
    )


def _dump_salience_full(runtime) -> str:
    sal = _get_salience(runtime)
    if not sal:
        return "SALIENCE: not enabled"
    return sal.dump()


def _salience_set(runtime, assembly_id: str, value: float) -> str:
    sal = _get_salience(runtime)
    if not sal:
        return "ERROR: salience not enabled"
    sal.set(assembly_id, float(value))
    return f"OK salience {assembly_id} = {value}"

def _set_hypothesis(runtime, assembly_id: str, hypothesis_id: str) -> str:
    reg = getattr(runtime, "hypothesis_registry", None)
    if not reg:
        return "ERROR: hypothesis system not enabled"

    reg.assign(assembly_id, hypothesis_id)
    return f"OK hypothesis {assembly_id} -> {hypothesis_id}"


def _salience_clear(runtime) -> str:
    sal = _get_salience(runtime)
    if not sal:
        return "ERROR: salience not enabled"
    sal.clear()
    return "OK salience cleared"


# ============================================================
# Striatum / BG diagnostics
# ============================================================

def _dump_striatum(runtime) -> str:
    snap = getattr(runtime, "_last_striatum_snapshot", None)
    if not snap:
        return "STRIATUM: no data"

    lines = [f"STRIATUM @ t={snap.get('time', 0.0):.3f}"]
    if snap.get("winner") is not None:
        lines.append(f"winner={snap['winner']}")

    for ch, val in sorted(
        snap.get("dominance", {}).items(),
        key=lambda x: x[1],
        reverse=True,
    ):
        lines.append(f"{ch}={val:.6f}")

    return "\n".join(lines)

def _dump_routing(runtime) -> str:
    snap = getattr(runtime, "_last_striatum_snapshot", None)
    if not snap:
        return "ROUTING: no data"

    routing = snap.get("routing", {})
    if not routing:
        return "ROUTING: empty"

    lines = ["ROUTING:"]
    for aid, ch in sorted(routing.items()):
        lines.append(f"  {aid} -> {ch}")
    return "\n".join(lines)

def _dump_hypotheses(runtime) -> str:
    gen = getattr(runtime, "hypothesis_generator", None)
    if not gen:
        return "HYPOTHESES: unavailable"

    snap = gen.snapshot()
    if not snap:
        return "HYPOTHESES: none"

    lines = ["HYPOTHESES:"]
    for aid, hid in sorted(snap.items()):
        lines.append(f"  {aid} -> {hid}")
    return "\n".join(lines)


def _dump_gate(runtime) -> str:
    if not hasattr(runtime, "snapshot_gate_state"):
        return "GATE: unavailable"

    s = runtime.snapshot_gate_state()
    decision = s.get("decision", False)
    return (
        "GATE:\n"
        f"  t={s.get('time', 0.0):.3f}\n"
        f"  relief={s.get('relief', 1.0):.4f}\n"
        f"  decision={'yes' if decision else 'no'}"
    )


def _dump_decision(runtime) -> str:
    if not hasattr(runtime, "get_decision_state"):
        return "DECISION: unsupported"

    d = runtime.get_decision_state()
    if not d:
        return "DECISION: none"

    return "DECISION:\n" + "\n".join(f"  {k}={v}" for k, v in d.items())

# ============================================================
# Affective Urgency diagnostics (read-only)
# ============================================================

def _dump_urgency(runtime) -> str:
    ua = getattr(runtime, "urgency_adapter", None)
    sig = getattr(runtime, "urgency_signal", None)

    if not ua or not sig:
        return "URGENCY: not enabled"

    snap = sig.snapshot()
    return (
        "URGENCY:\n"
        f"  value={ua.last_urgency:.4f}\n"
        f"  enabled={snap.get('enabled', False)}"
    )


def _dump_urgency_trace(runtime) -> str:
    tr = getattr(runtime, "urgency_trace", None)
    if not tr:
        return "URGENCY_TRACE: not enabled"

    summary = tr.summary()
    return (
        "URGENCY_TRACE:\n"
        f"  count={summary.get('count', 0)}\n"
        f"  mean={summary.get('mean_urgency', 0.0):.4f}\n"
        f"  max={summary.get('max_urgency', 0.0):.4f}"
    )


# ============================================================
# VTA Value diagnostics
# ============================================================

def _dump_value(runtime) -> str:
    val = getattr(runtime, "value_signal", None)
    if not val:
        return "VALUE: not enabled"

    return f"VALUE: {val.get():.4f}"


def _set_value(runtime, x: float) -> str:
    val = getattr(runtime, "value_signal", None)
    pol = getattr(runtime, "value_policy", None)

    if not val or not pol:
        return "ERROR: value system not enabled"

    t = getattr(runtime, "time", 0.0)

    new_val = pol.apply(
        current_value=val.get(),
        proposed_value=float(x),
        t=t,
    )

    val.set(new_val)
    return f"OK value = {val.get():.4f}"


def _clear_value(runtime) -> str:
    val = getattr(runtime, "value_signal", None)
    if not val:
        return "ERROR: value system not enabled"

    val.reset()
    return "OK value reset"

def _dump_working(runtime) -> str:
    wa = getattr(runtime, "pfc_adapter", None)
    if not wa:
        return "WORKING: unavailable"
    return "WORKING:\n" + json.dumps(wa.snapshot(), indent=2)

def _dump_fx(runtime) -> str:
    """
    Decision FX snapshot (JSON) for tests.

    Always returns JSON (or an ERROR string).
    """
    if hasattr(runtime, "snapshot_decision_fx"):
        snap = runtime.snapshot_decision_fx()
        return json.dumps(snap, indent=2)

    # fallback if you didn't add snapshot_decision_fx yet
    if hasattr(runtime, "get_decision_fx_state"):
        snap = runtime.get_decision_fx_state()
        return json.dumps({"enabled": True, "bundle": snap}, indent=2)

    return "ERROR: Decision FX not supported by runtime"


# ============================================================
# Latch controls
# ============================================================

def _set_sustain(runtime, n: int) -> str:
    try:
        runtime._decision_sustain_required = max(1, int(n))
        return f"OK sustain {n}"
    except Exception as e:
        return f"ERROR: {e}"

def _force_commit(runtime) -> str:
    """
    TEST-ONLY.

    Forces a temporary decision coincidence window so the
    decision latch may fire naturally on the next steps.

    Does NOT:
    - choose a winner
    - bypass latch logic
    - alter thresholds
    """

    if not hasattr(runtime, "inject_decision_coincidence"):
        return "ERROR: force_commit not supported by runtime"

    runtime.inject_decision_coincidence(
        delta_boost=runtime.DECISION_DOMINANCE_THRESHOLD,
        relief_boost=runtime.DECISION_RELIEF_THRESHOLD,
        steps=max(1, runtime._decision_sustain_required),
    )

    return "OK force_commit armed"


def _get_sustain(runtime) -> str:
    return f"SUSTAIN: {getattr(runtime, '_decision_sustain_required', '?')}"


def _reset_latch(runtime) -> str:
    runtime._decision_fired = False
    runtime._decision_counter = 0
    runtime._decision_state = None
    return "OK reset_latch"


# ============================================================
# TCP Server
# ============================================================

def start_command_server(runtime, host: str = "127.0.0.1", port: int = 5557):

    def help_text() -> str:
        return (
            "Commands:\n"
            "  poke <region> <mag>\n"
            "  poke_pop <region> <population> <mag>\n"
            "  poke_asm <region> <population> <idx> <mag>\n"
            "  stats <region>\n"
            "  stats_pop <region> <population>\n"
            "  delta_pop <region> <populationA> <populationB>\n"
            "  top <region> <N>\n"
            "  context | ctx\n"
            "  ctxfull\n"
            "  salience\n"
            "  salience_full\n"
            "  salience_set <assembly> <value>\n"
            "  salience_clear\n"
            "  striatum | stri\n"
            "  gate\n"
            "  decision\n"
            "  sustain [N]\n"
            "  reset_latch\n"
            "  force_commit\n"
            "  control\n"
            "  value\n"
            "  value_set <x>\n"
            "  urgency\n"
            "  urgency_trace\n"
            "  value_clear\n"
            "  routing\n"
            "  hypothesis_set <assembly> <hypothesis>\n"
            "  hypothesis_reset\n"
            "  hypotheses\n"
            "  working\n"
            "  fx, or decision_fx\n"
            "  dump_asm <region>\n"
            "  help"
        )

    def handle(cmd: str) -> str:
        parts = cmd.strip().split()
        if not parts:
            return "ERROR: empty command"

        op = parts[0].lower()

        if op == "reset_latch":
            return _reset_latch(runtime)

        if op == "force_commit":
            return _force_commit(runtime)


        if op in ("help", "?"):
            return help_text()

        if op == "poke" and len(parts) == 3:
            runtime.inject_stimulus(parts[1], magnitude=float(parts[2]))
            return "OK"

        if op == "poke_pop" and len(parts) == 4:
            runtime.inject_stimulus(parts[1], parts[2], magnitude=float(parts[3]))
            return "OK"

        if op == "poke_asm" and len(parts) == 5:
            runtime.inject_stimulus(parts[1], parts[2], int(parts[3]), float(parts[4]))
            return "OK"

        if op == "stats" and len(parts) == 2:
            return _region_stats(runtime, parts[1])
        
        if op == "stats_pop" and len(parts) == 3:
            return _population_stats(runtime, parts[1], parts[2])

        if op == "delta_pop" and len(parts) == 4:
            return _delta_population(runtime, parts[1], parts[2], parts[3])

        if op == "top" and len(parts) == 3:
            return _top_assemblies(runtime, parts[1], int(parts[2]))

        if op == "top":
            return "ERROR: usage top <region> <N>"
        
        if op == "dump_asm" and len(parts) == 2:
            return _dump_assemblies_json(runtime, parts[1])       

        if op in ("context", "ctx"):
            return _dump_context(runtime)

        if op == "ctxfull":
            return _dump_context_full(runtime)

        if op == "salience":
            return _dump_salience(runtime)

        if op == "salience_full":
            return _dump_salience_full(runtime)

        if op == "salience_set" and len(parts) == 3:
            return _salience_set(runtime, parts[1], float(parts[2]))

        if op == "salience_clear":
            return _salience_clear(runtime)

        if op in ("striatum", "stri"):
            return _dump_striatum(runtime)

        if op == "gate":
            return _dump_gate(runtime)

        if op == "decision":
            return _dump_decision(runtime)

        if op == "sustain":
            return _get_sustain(runtime) if len(parts) == 1 else _set_sustain(runtime, int(parts[1]))

        if op == "control":
            return _dump_control(runtime)
        
        if op == "value":
            return _dump_value(runtime)
        
        if op == "working":
            return _dump_working(runtime)


        if op == "value_set" and len(parts) == 2:
            try:
                x = float(parts[1])
            except ValueError:
                return "ERROR: invalid value"
            return _set_value(runtime, x)

        if op == "value_clear":
            return _clear_value(runtime)
        
        if op == "routing":
            return _dump_routing(runtime)
        
        if op == "hypotheses":
            return _dump_hypotheses(runtime)
        
        if op == "hypothesis_set" and len(parts) == 3:
            return _set_hypothesis(runtime, parts[1], parts[2])

        if op in ("fx", "decision_fx"):
            return _dump_fx(runtime)

        if op == "hypothesis_reset":
            return _reset_hypotheses(runtime)

        # -----------------------------
        # Affective urgency (read-only)
        # -----------------------------
        if op == "urgency":
            return _dump_urgency(runtime)

        if op == "urgency_trace":
            return _dump_urgency_trace(runtime)

        # -----------------------------
        # Pre-decision salience priming
        # -----------------------------
        if op == "psm_prime" and len(parts) == 3:
            target = parts[1]
            try:
                gain = float(parts[2])
            except ValueError:
                return "ERROR: invalid gain"

            if not hasattr(runtime, "apply_psm_prime"):
                return "ERROR: PSM not supported"

            runtime.apply_psm_prime(target, gain)
            return f"OK psm_prime {target} += {gain}"

        return "ERROR: unknown command"

    def loop():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            s.listen(5)
            print(f"[CMD] Listening on {host}:{port}")

            while True:
                conn, _ = s.accept()
                with conn:
                    data = conn.recv(4096)
                    if not data:
                        continue
                    try:
                        resp = handle(data.decode("utf-8"))
                    except Exception as e:
                        resp = f"ERROR: {e}"
                    conn.sendall((resp + "\n").encode("utf-8"))

    threading.Thread(target=loop, daemon=True).start()
