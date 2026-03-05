from __future__ import annotations

from pathlib import Path
from typing import List

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

DT = 0.01

BASELINE_STEPS = 200
PROBE_STEPS = 200
SALIENCE_STEPS = 400
POST_SALIENCE_STEPS = 300

MD_PROBE_MAG = 0.25
SALIENCE_DELTA = 0.20

ROOT = Path("C:/Users/Admin/Desktop/neural framework")


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def striatum_delta(rt: BrainRuntime) -> float:
    pops = rt.region_states["striatum"]["populations"]
    d1 = sum(p.output() for p in pops["D1_MSN"])
    d2 = sum(p.output() for p in pops["D2_MSN"])
    return abs(d1 - d2)


def gpi_relief(rt: BrainRuntime) -> float:
    return rt.snapshot_gate_state()["relief"]


# ------------------------------------------------------------
# Test
# ------------------------------------------------------------

def main() -> None:
    print("=== TEST: Salience Characterization (instrumented, no asserts) ===")

    loader = NeuralFrameworkLoader(ROOT)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="human_default",
        state_profile="awake",
        compound_profile="experimental",
    )

    rt = BrainRuntime(brain, dt=DT)

    # --------------------------------------------------
    # Phase A — Baseline
    # --------------------------------------------------

    baseline_deltas: List[float] = []

    for _ in range(BASELINE_STEPS):
        rt.step()
        baseline_deltas.append(striatum_delta(rt))

    baseline_mean = sum(baseline_deltas) / len(baseline_deltas)
    baseline_max = max(baseline_deltas)

    print(f"[BASELINE] mean delta = {baseline_mean:.6f}")
    print(f"[BASELINE] max  delta = {baseline_max:.6f}")

    # --------------------------------------------------
    # Phase B — Tonic MD probe (no salience)
    # --------------------------------------------------

    for _ in range(PROBE_STEPS):
        rt.inject_stimulus("md", magnitude=MD_PROBE_MAG)
        rt.step()

    # --------------------------------------------------
    # Phase C — Probe + salience
    # --------------------------------------------------

    peak_delta = 0.0
    gate_violations = 0
    decision_events = 0

    striatum = rt.region_states["striatum"]["populations"]
    d1_assemblies = striatum["D1_MSN"]

    for step in range(SALIENCE_STEPS):
        rt.inject_stimulus("md", magnitude=MD_PROBE_MAG)

        for p in d1_assemblies:
            rt.salience.inject(p.assembly_id, SALIENCE_DELTA)

        rt.step()

        delta = striatum_delta(rt)
        peak_delta = max(peak_delta, delta)

        relief = gpi_relief(rt)
        if relief < rt.DECISION_RELIEF_THRESHOLD:
            gate_violations += 1
            print(
                f"[WARN][SALIENCE] GPi relief dipped: "
                f"{relief:.4f} at step {rt.step_count}"
            )

        if rt.get_decision_state() is not None:
            decision_events += 1
            print(
                f"[WARN][SALIENCE] Decision fired at "
                f"step {rt.step_count}: {rt.get_decision_state()}"
            )

    print(f"[SALIENCE] peak delta = {peak_delta:.6f}")
    print(f"[SALIENCE] gate violations = {gate_violations}")
    print(f"[SALIENCE] decision events = {decision_events}")

    # --------------------------------------------------
    # Phase D — Salience removed, probe continues
    # --------------------------------------------------

    post_deltas: List[float] = []
    post_gate_violations = 0
    post_decisions = 0

    for _ in range(POST_SALIENCE_STEPS):
        rt.inject_stimulus("md", magnitude=MD_PROBE_MAG)
        rt.step()

        post_deltas.append(striatum_delta(rt))

        relief = gpi_relief(rt)
        if relief < rt.DECISION_RELIEF_THRESHOLD:
            post_gate_violations += 1
            print(
                f"[WARN][POST] GPi relief dipped: "
                f"{relief:.4f} at step {rt.step_count}"
            )

        if rt.get_decision_state() is not None:
            post_decisions += 1
            print(
                f"[WARN][POST] Decision fired at "
                f"step {rt.step_count}: {rt.get_decision_state()}"
            )

    post_mean = sum(post_deltas) / len(post_deltas)
    post_peak = max(post_deltas)

    print(f"[POST] mean delta = {post_mean:.6f}")
    print(f"[POST] peak delta = {post_peak:.6f}")
    print(f"[POST] gate violations = {post_gate_violations}")
    print(f"[POST] decision events = {post_decisions}")

    print("=== TEST COMPLETE (observational run) ===")


if __name__ == "__main__":
    main()
