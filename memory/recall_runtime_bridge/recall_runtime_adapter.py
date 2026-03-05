from typing import Dict, Any

from engine.execution.execution_target import ExecutionTarget
from engine.execution.execution_gate import ExecutionGate

from memory.influence_arbitration.influence_packet import InfluencePacket
from .recall_runtime_result import RecallRuntimeResult
from .recall_runtime_policy import RecallRuntimePolicy


class RecallRuntimeAdapter:

    def apply_packet(
        self,
        packet: InfluencePacket,
        gate: ExecutionGate,
        identity_map: Dict[str, float],
    ) -> RecallRuntimeResult:

        if not RecallRuntimePolicy.ENABLE_RECALL_EXECUTION:
            return RecallRuntimeResult(applied_targets={})

        applied: Dict[str, Any] = {}

        for target_name, magnitude in packet.targets.items():

            # -----------------------------
            # Normalize target to enum
            # -----------------------------
            if isinstance(target_name, ExecutionTarget):
                enum_target = target_name
                target_key = target_name.name
            else:
                target_key = str(target_name)
                enum_target = ExecutionTarget[target_key]

            # -----------------------------
            # Identity lookup remains string-based
            # -----------------------------
            identity = identity_map.get(target_key, 0.0)

            result = gate.apply(
                target=enum_target,
                value=magnitude,
                identity=identity,
            )

            applied[target_key] = result

        return RecallRuntimeResult(applied_targets=applied)