# dry_run_mapper.py
from __future__ import annotations

from engine.execution_binding.binding_map import BindingMap
from engine.execution_binding.binding_result import BindingResult

from .dry_run_request import DryRunRequest
from .dry_run_result import DryRunResult
from .dry_run_trace import DryRunTrace

FORBIDDEN_RUNTIME_TARGETS = {
    "runtime",
    "decision",
    "learning",
    "salience",
    "value",
    "urgency",
    "routing",
}

class DryRunMapper:
    """
    Maps bindings into a dry-run simulation.
    Emits trace records only.
    """

    def simulate(
        self,
        *,
        request: DryRunRequest,
        binding_map: BindingMap,
        binding_result: BindingResult,
    ) -> DryRunTrace:
        results = []

        for target in binding_result.bound_targets:
            if target in FORBIDDEN_RUNTIME_TARGETS:
                results.append(
                    DryRunResult(
                        intent_id=request.intent.intent_id,
                        simulated_targets=(target,),
                        allowed=False,
                        reason="runtime_target_blocked",
                    )
                )
            else:
                results.append(
                    DryRunResult(
                        intent_id=request.intent.intent_id,
                        simulated_targets=(target,),
                        allowed=False,
                        reason="dry_run_only",
                    )
                )

        return DryRunTrace(results=results)
