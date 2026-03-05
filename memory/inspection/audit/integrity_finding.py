from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Literal


Severity = Literal["ERROR", "WARNING", "INFO"]


@dataclass(frozen=True)
class IntegrityFinding:
    """
    Immutable forensic finding produced by an integrity audit.

    This object:
    - describes a detected inconsistency
    - carries NO authority
    - suggests NO action
    - is safe to log, export, or discard
    """

    audit_id: str
    finding_id: str
    severity: Severity
    layer: str

    description: str

    evidence: Dict[str, Any]
