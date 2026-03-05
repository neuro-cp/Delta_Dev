from dataclasses import dataclass


@dataclass(frozen=True)
class LearningAuditReport:
    passed: bool
    finding_count: int
    notes: str | None = None
