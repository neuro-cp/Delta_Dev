from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OperatorExecutionRecord:
    """
    Immutable audit record for operator execution governance.
    """
    operator_id: str
    approved: bool
    request_snapshot: Any
