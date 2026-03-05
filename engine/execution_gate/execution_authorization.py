# execution_authorization.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import time

@dataclass(frozen=True)
class ExecutionAuthorization:
    """
    Explicit, time-bounded authorization.
    """
    authorized: bool
    expires_at: Optional[float] = None

    def is_valid(self) -> bool:
        if not self.authorized:
            return False
        if self.expires_at is None:
            return True
        return time.time() <= self.expires_at
