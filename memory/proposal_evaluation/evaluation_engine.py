from __future__ import annotations
from typing import Iterable, List

from memory.proposal_evaluation.evaluation_record import EvaluationRecord
from memory.proposal_evaluation.veto_record import VetoRecord


class EvaluationEngine:
    """
    Read-only evaluation engine.

    No execution.
    No proposal modification.
    No ordering.
    """

    def evaluate(
        self,
        *,
        proposal_ids: Iterable[str],
        evaluator_id: str,
        policy_id: str,
    ) -> List[EvaluationRecord]:
        return [
            EvaluationRecord(
                proposal_id=p,
                evaluator_id=evaluator_id,
                policy_id=policy_id,
                accepted=False,
                rationale=None,
            )
            for p in proposal_ids
        ]

    def veto(
        self,
        *,
        proposal_ids: Iterable[str],
        veto_policy_id: str,
    ) -> List[VetoRecord]:
        return [
            VetoRecord(
                proposal_id=p,
                veto_policy_id=veto_policy_id,
                vetoed=False,
                rationale=None,
            )
            for p in proposal_ids
        ]
