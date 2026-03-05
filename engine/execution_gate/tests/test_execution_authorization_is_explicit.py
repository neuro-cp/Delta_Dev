# test_execution_authorization_is_explicit.py
from engine.execution_gate.execution_authorization import ExecutionAuthorization
import time

def test_execution_authorization_expiry():
    auth = ExecutionAuthorization(authorized=True, expires_at=time.time() - 1)
    assert auth.is_valid() is False
