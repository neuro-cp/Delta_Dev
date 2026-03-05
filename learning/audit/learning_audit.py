from __future__ import annotations

from typing import Iterable, Set

from learning.schemas.learning_proposal import LearningProposal
from learning.audit.learning_audit_report import LearningAuditReport


class LearningAudit:
    """
    Hard gate for learning session.

    CONTRACT:
    - Pure
    - Deterministic
    - No mutation
    - No side effects
    - Must fail loudly on structural violations
    """

    def audit(
        self,
        *,
        proposals: Iterable[LearningProposal],
    ) -> LearningAuditReport:

        proposal_ids: Set[str] = set()
        delta_targets: Set[str] = set()

        finding_count = 0
        notes = []

        for proposal in proposals:

            if proposal.proposal_id in proposal_ids:
                finding_count += 1
                notes.append("duplicate_proposal_id")
            proposal_ids.add(proposal.proposal_id)

            if not proposal.deltas:
                finding_count += 1
                notes.append("empty_proposal")

            for delta in proposal.deltas:
                if delta.target in delta_targets:
                    finding_count += 1
                    notes.append("duplicate_delta_target")
                delta_targets.add(delta.target)

            if not proposal.bounded:
                finding_count += 1
                notes.append("unbounded_proposal")

            if not proposal.replay_consistent:
                finding_count += 1
                notes.append("replay_inconsistent")

        passed = finding_count == 0

        report = LearningAuditReport(
            passed=passed,
            finding_count=finding_count,
            notes=";".join(notes) if notes else None,
        )

        if not passed:
            raise AssertionError(
                f"LearningAudit structural violation: {report.notes}"
            )

        return report