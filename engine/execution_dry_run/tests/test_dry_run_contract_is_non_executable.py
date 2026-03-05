# test_dry_run_contract_is_non_executable.py
from engine.execution_dry_run.dry_run_contract import DryRunContract

def test_dry_run_contract_is_non_executable():
    c = DryRunContract()
    assert c.execution_allowed is False
