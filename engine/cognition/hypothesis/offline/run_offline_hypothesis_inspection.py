from __future__ import annotations

from typing import Dict, List

from engine.salience.tools.read_salience_log import (
    read_salience_log_as_step_scalar,
)

from engine.cognition.hypothesis.offline.observation_frame import ObservationFrame
from engine.cognition.hypothesis.offline.hypothesis_runner import HypothesisRunner
from engine.cognition.hypothesis.offline.support_to_activation import SupportToActivation

from engine.cognition.hypothesis.hypothesis_registry import HypothesisRegistry
from engine.cognition.hypothesis.hypothesis_grounding import HypothesisGrounding
from engine.cognition.hypothesis.hypothesis_competition import HypothesisCompetition
from engine.cognition.hypothesis.hypothesis_dynamics import HypothesisDynamics
from engine.cognition.hypothesis.hypothesis_stabilization import HypothesisStabilization
from engine.cognition.hypothesis.hypothesis_bias import HypothesisBias

from engine.cognition.hypothesis.offline.inspection.hypothesis_timeline_builder import (
    HypothesisTimelineBuilder,
)
from engine.cognition.hypothesis.offline.render_hypothesis_timeline import (
    print_hypothesis_bundle,
)


# --------------------------------------------------
# Configuration (inspection only)
# --------------------------------------------------

SALIENCE_LOG_PATH = "engine/salience/tests/salience_trace_proof_log.txt"
WINDOW_SIZE = 50


def main() -> None:
    # --------------------------------------------------
    # 1) Load real salience trace
    # --------------------------------------------------

    salience_by_step: Dict[int, float] = read_salience_log_as_step_scalar(
        SALIENCE_LOG_PATH
    )

    if not salience_by_step:
        raise RuntimeError("Salience trace is empty.")

    steps = sorted(salience_by_step.keys())
    window_start = steps[0]
    window_end = window_start + WINDOW_SIZE

    salience_by_step = {
        s: salience_by_step[s]
        for s in steps
        if window_start <= s <= window_end
    }

    # --------------------------------------------------
    # 2) Build ObservationFrames
    # --------------------------------------------------

    frames: List[ObservationFrame] = []

    for step in range(window_start, window_end + 1):
        sal = salience_by_step.get(step, 0.0)
        frames.append(
            ObservationFrame(
                step=step,
                salience=sal,
                assembly_outputs={"salience": sal},
            )
        )

    # --------------------------------------------------
    # 3) Hypothesis stack (offline)
    # --------------------------------------------------

    registry = HypothesisRegistry()
    h1 = registry.create(hypothesis_id="H1", created_step=0)
    h2 = registry.create(hypothesis_id="H2", created_step=0)

    runner = HypothesisRunner(
        registry=registry,
        grounding=HypothesisGrounding(),
        competition=HypothesisCompetition(),
        dynamics=HypothesisDynamics(),
        stabilization=HypothesisStabilization(
            activation_threshold=0.6,
            sustain_steps=3,
        ),
        bias=HypothesisBias(),
        support_mapper=SupportToActivation(
            gain=5.0,
            midpoint=0.4,
        ),
    )

    # --------------------------------------------------
    # 4) Step offline cognition
    # --------------------------------------------------

    for f in frames:
        h1.support += float(f.salience or 0.0)
        h2.support += 0.005
        runner.step(f)

    # --------------------------------------------------
    # 5) Build + render timelines
    # --------------------------------------------------

    builder = HypothesisTimelineBuilder(runner=runner)
    bundle = builder.build()

    print_hypothesis_bundle(bundle, max_rows=25)


if __name__ == "__main__":
    main()
