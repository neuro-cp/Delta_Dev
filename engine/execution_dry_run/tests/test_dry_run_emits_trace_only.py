# test_dry_run_emits_trace_only.py
from engine.execution_dry_run.dry_run_mapper import DryRunMapper
from engine.execution_dry_run.dry_run_request import DryRunRequest
from engine.execution_gate.execution_intent import ExecutionIntent
from engine.execution_binding.binding_map import BindingMap
from engine.execution_binding.binding_result import BindingResult
from engine.execution_binding.binding_target import BindingTarget
from engine.execution_dry_run.dry_run_trace import DryRunTrace

def test_dry_run_emits_trace_only():
    mapper = DryRunMapper()
    intent = ExecutionIntent("i3", ("attention",))
    req = DryRunRequest(intent, ("attention",))
    bmap = BindingMap("i3", (BindingTarget("attention"),))
    bres = BindingResult("i3", ("attention",), True, "ok")

    trace = mapper.simulate(
        request=req,
        binding_map=bmap,
        binding_result=bres,
    )
    assert isinstance(trace, DryRunTrace)
