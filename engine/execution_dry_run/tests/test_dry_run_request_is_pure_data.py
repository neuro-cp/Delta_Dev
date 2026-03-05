# test_dry_run_request_is_pure_data.py
from engine.execution_dry_run.dry_run_request import DryRunRequest
from engine.execution_gate.execution_intent import ExecutionIntent

def test_dry_run_request_is_pure_data():
    intent = ExecutionIntent("i1", ("attention",))
    req = DryRunRequest(intent, ("attention",))
    assert req.intent.intent_id == "i1"
