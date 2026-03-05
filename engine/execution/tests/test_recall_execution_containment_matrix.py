from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime
from engine.execution.execution_state import ExecutionState
from engine.execution.execution_target import ExecutionTarget
from memory.recall_runtime_bridge.recall_runtime_policy import RecallRuntimePolicy


TOL = 1e-9
STEPS = 10


# ------------------------------------------------------------
# Stub matching ReplayRecallPipeline interface
# ------------------------------------------------------------

class _Suggestion:
    def __init__(self, target, magnitude: float):
        self.target = target
        self.magnitude = magnitude


class DeterministicRecallStub:
    def query(self, runtime):
        return [
            _Suggestion(ExecutionTarget.VALUE_BIAS, 0.25),
        ]


# ------------------------------------------------------------
# Runtime builder
# ------------------------------------------------------------

def build_runtime():
    repo_root = Path(__file__).resolve().parents[3]

    loader = NeuralFrameworkLoader(repo_root)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="human_default",
        state_profile="awake",
        compound_profile="experimental",
    )

    return BrainRuntime(brain, dt=0.01)


# ------------------------------------------------------------
# Case runner
# ------------------------------------------------------------

def run_case(executive_enabled: bool, recall_enabled: bool):
    runtime = build_runtime()

    runtime.enable_vta_value = True
    runtime.enable_decision_bias = True

    RecallRuntimePolicy.ENABLE_RECALL_EXECUTION = True

    state = ExecutionState(enabled=executive_enabled)
    runtime.execution_state = state
    runtime.execution_gate._state = state

    # Seed a baseline decision bias
    runtime.decision_bias.apply_decision(
        winner="D1_MSN",
        channels=["D1_MSN", "D2_MSN"],
        strength=1.0,
        step=0,
    )

    runtime._recall_pipeline = DeterministicRecallStub() if recall_enabled else None

    snapshots = []
    for _ in range(STEPS):
        runtime.step()
        snapshots.append(dict(runtime.decision_bias.dump()))

    return snapshots


# ------------------------------------------------------------
# Comparison helpers
# ------------------------------------------------------------

def bias_maps_equal(a, b):
    for map_a, map_b in zip(a, b):
        if set(map_a.keys()) != set(map_b.keys()):
            return False
        for k in map_a:
            if abs(map_a[k] - map_b[k]) > TOL:
                return False
    return True


def first_diff(a, b):
    for i, (map_a, map_b) in enumerate(zip(a, b)):
        if set(map_a.keys()) != set(map_b.keys()):
            return i, map_a, map_b
        for k in map_a:
            if abs(map_a[k] - map_b[k]) > TOL:
                return i, map_a, map_b
    return None


# ------------------------------------------------------------
# Containment test
# ------------------------------------------------------------

def test_recall_execution_containment_matrix():

    baseline = run_case(False, False)
    off_with_recall = run_case(False, True)
    on_with_recall = run_case(True, True)

    # Executive OFF must block recall influence
    assert bias_maps_equal(
        baseline, off_with_recall
    ), "Leakage detected: recall influenced runtime with executive OFF."

    # Executive ON must allow recall influence
    d = first_diff(baseline, on_with_recall)

    assert d is not None, \
        "Bridge dead: recall did not influence runtime with executive ON."

    step, a, b = d
    print(f"\nDIFF step={step}\n  baseline={a}\n  on+recall={b}")

    RecallRuntimePolicy.ENABLE_RECALL_EXECUTION = False