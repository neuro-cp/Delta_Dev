from __future__ import annotations

import time
from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime
from engine.command_server import start_command_server

from engine.salience.salience_field import SalienceField
from engine.salience.salience_engine import SalienceEngine

from engine.salience.sources.surprise_source import SurpriseSource
from engine.salience.sources.competition_source import CompetitionSource
from engine.salience.sources.persistence_source import PersistenceSource


# ============================================================
# CONFIG
# ============================================================

ROOT = Path(__file__).resolve().parents[2]   # project root
DT = 0.01
STEPS = 60
SLEEP = 0.01


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("=== RUNTIME + SALIENCE ENGINE SMOKE TEST ===")

    # --------------------------------------------------------
    # Load + compile brain
    # --------------------------------------------------------
    loader = NeuralFrameworkLoader(ROOT)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="minimal",
        state_profile="awake",
        compound_profile="experimental",
    )

    # --------------------------------------------------------
    # Runtime
    # --------------------------------------------------------
    runtime = BrainRuntime(brain, dt=DT)

    # --------------------------------------------------------
    # Salience system (engine-authoritative)
    # --------------------------------------------------------
    salience_field = SalienceField(
        decay_tau=3.0,
        max_value=1.0,
    )

    salience_engine = SalienceEngine(
        sources=[
            SurpriseSource(),
            CompetitionSource(),
            PersistenceSource(),
        ]
    )

    # --------------------------------------------------------
    # Command server (inspection only)
    # --------------------------------------------------------
    start_command_server(runtime)

    print("[OK] Runtime initialized")
    print("[OK] Salience field initialized")
    print("[OK] Salience engine initialized")
    print("[OK] Command server running\n")

    # --------------------------------------------------------
    # Stepping loop
    # --------------------------------------------------------
    for step in range(STEPS):
        runtime.step()

        # Salience runs AFTER physiology, BEFORE decay
        salience_engine.step(runtime, salience_field)

        if step % 10 == 0:
            gate = runtime.snapshot_gate_state()
            sal = salience_field.dump()

            max_sal = max(sal.values()) if sal else 0.0

            print(
                f"[STEP {step:03d}] "
                f"t={gate['time']:.3f} "
                f"relief={gate['relief']:.3f} "
                f"winner={gate.get('winner')} "
                f"salience_keys={len(sal)} "
                f"max_salience={max_sal:.4f}"
            )

        time.sleep(SLEEP)

    print("\n=== SALIENCE ENGINE SMOKE TEST COMPLETE ===")
    print("Try commands: help, gate, striatum, decision")


if __name__ == "__main__":
    main()
