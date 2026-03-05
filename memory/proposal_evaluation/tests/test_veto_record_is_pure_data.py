from memory.proposal_evaluation.veto_record import VetoRecord


def test_veto_record_has_no_numeric_fields() -> None:
    record = VetoRecord(
        proposal_id="p1",
        veto_policy_id="policy",
        vetoed=False,
        rationale=None,
    )

    for v in record.__dict__.values():
        assert not (
            isinstance(v, (int, float)) and not isinstance(v, bool)
        )
