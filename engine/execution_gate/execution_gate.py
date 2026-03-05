# execution_gate.py
from __future__ import annotations
from typing import FrozenSet

from .execution_intent import ExecutionIntent
from .execution_authorization import ExecutionAuthorization
from .execution_scope import ExecutionScope
from .execution_record import ExecutionRecord

class ExecutionGate:
    """
    Single execution choke point.

    Emits records only. Never executes.
    """

    def __init__(self, scope: ExecutionScope):
        self._scope = scope

    def attempt(
        self,
        intent: ExecutionIntent,
        authorization: ExecutionAuthorization,
    ) -> ExecutionRecord:
        targets = frozenset(intent.targets)

        try:
            self._scope.validate(targets)
        except Exception as e:
            return ExecutionRecord(
                intent_id=intent.intent_id,
                targets=intent.targets,
                authorized=False,
                executed=False,
                reason=str(e),
            )

        if not authorization.is_valid():
            return ExecutionRecord(
                intent_id=intent.intent_id,
                targets=intent.targets,
                authorized=False,
                executed=False,
                reason="authorization_invalid",
            )

        return ExecutionRecord(
            intent_id=intent.intent_id,
            targets=intent.targets,
            authorized=True,
            executed=False,
            reason="execution_disabled",
        )
