from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime
from engine.execution.execution_target import ExecutionTarget
from memory.influence_arbitration.influence_packet import InfluencePacket


from engine.execution.execution_state import ExecutionState
from engine.execution.execution_gate import ExecutionGate

def _build_runtime() -> BrainRuntime:
    root = Path(__file__).resolve().parents[3]

    loader = NeuralFrameworkLoader(root)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="minimal",
        state_profile="awake",
        compound_profile="experimental",
    )

    rt = BrainRuntime(brain)

    # Replace execution state properly (immutable pattern)
    rt.execution_state = ExecutionState(enabled=True)
    rt.execution_gate = ExecutionGate(rt.execution_state)

    return rt


def test_recall_adapter_direct_probe():
    print("\n================ DIRECT ADAPTER PROBE ==================")

    rt = _build_runtime()

    # --------------------------------------------------
    # 1. Manually create packet
    # --------------------------------------------------
    manual_packet = InfluencePacket(
        targets={
            ExecutionTarget.VALUE_BIAS: 0.42
        }
    )

    print("\n[MANUAL PACKET]")
    print(manual_packet.targets)

    # --------------------------------------------------
    # 2. Send directly to adapter (no pipeline)
    # --------------------------------------------------
    if rt.recall_runtime_adapter is None:
        print("\n[ERROR] recall_runtime_adapter is None")
        return

    result = rt.recall_runtime_adapter.apply_packet(
        packet=manual_packet,
        gate=rt.execution_gate,
        identity_map={
            ExecutionTarget.VALUE_BIAS: 0.0
        },
    )

    print("\n[ADAPTER OUTPUT]")
    print(result.applied_targets)

    print("\n================ END PROBE ==================")