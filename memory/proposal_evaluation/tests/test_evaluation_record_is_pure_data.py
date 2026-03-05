from memory.proposal_evaluation.evaluation_record import EvaluationRecord


def test_evaluation_record_has_no_numeric_fields() -> None:
    record = EvaluationRecord(
        proposal_id="p1",
        evaluator_id="eval",
        policy_id="policy",
        accepted=False,
        rationale=None,
    )

    for v in record.__dict__.values():
        assert not (
            isinstance(v, (int, float)) and not isinstance(v, bool)
        )
