# test_dry_run_blocks_runtime_targets.py
from engine.execution_dry_run.dry_run_mapper import DryRunMapper
from engine.execution_dry_run.dry_run_request import DryRunRequest
from engine.execution_gate.execution_intent import ExecutionIntent
from engine.execution_binding.binding_map import BindingMap
from engine.execution_binding.binding_result import BindingResult
from engine.execution_binding.binding_target import BindingTarget

def test_dry_run_blocks_runtime_targets():
    mapper = DryRunMapper()
    intent = ExecutionIntent("i4", ("runtime",))
    req = DryRunRequest(intent, ("runtime",))
    bmap = BindingMap("i4", (BindingTarget("runtime"),))
    bres = BindingResult("i4", ("runtime",), True, "ok")

    trace = mapper.simulate(
        request=req,
        binding_map=bmap,
        binding_result=bres,
    )
    assert trace.results[0].allowed is False
