from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List

from memory.inspection.audit.integrity_finding import IntegrityFinding


class IntegrityAudit(ABC):
    """
    Base class for offline integrity audits.

    An IntegrityAudit:
    - is read-only
    - is deterministic
    - does NOT mutate state
    - does NOT influence runtime
    """

    audit_id: str

    @abstractmethod
    def run(self) -> List[IntegrityFinding]:
        """
        Execute the audit and return zero or more findings.

        Findings describe violations or anomalies.
        Absence of ERROR findings implies audit pass.
        """
        raise NotImplementedError
