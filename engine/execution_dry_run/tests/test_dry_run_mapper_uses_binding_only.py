# test_dry_run_mapper_uses_binding_only.py
from engine.execution_dry_run.dry_run_mapper import DryRunMapper
from engine.execution_dry_run.dry_run_request import DryRunRequest
from engine.execution_gate.execution_intent import ExecutionIntent
from engine.execution_binding.binding_map import BindingMap
from engine.execution_binding.binding_result import BindingResult
from engine.execution_binding.binding_target import BindingTarget

def test_dry_run_mapper_uses_binding_only():
    mapper = DryRunMapper()
    intent = ExecutionIntent("i2", ("attention",))
    req = DryRunRequest(intent, ("attention",))
    bmap = BindingMap("i2", (BindingTarget("attention"),))
    bres = BindingResult("i2", ("attention",), True, "ok")

    trace = mapper.simulate(
        request=req,
        binding_map=bmap,
        binding_result=bres,
    )
    assert len(trace.results) == 1
