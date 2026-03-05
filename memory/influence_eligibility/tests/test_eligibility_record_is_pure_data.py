from __future__ import annotations

from memory.influence_eligibility.eligibility_record import (
    InfluenceEligibilityRecord,
)


def test_eligibility_record_is_immutable() -> None:
    record = InfluenceEligibilityRecord(
        artifact_id="artifact:1",
        artifact_type="semantic_grounding",
        eligibility_policy_id="policy:v1",
        eligible=True,
        rationale=None,
    )

    try:
        record.eligible = False  # type: ignore[misc]
        mutated = True
    except Exception:
        mutated = False

    assert mutated is False


def test_eligibility_record_has_no_numeric_magnitudes() -> None:
    """
    Eligibility may contain boolean state,
    but must not contain numeric magnitudes
    (weights, strengths, confidences, scores).
    """

    record = InfluenceEligibilityRecord(
        artifact_id="artifact:1",
        artifact_type="semantic_grounding",
        eligibility_policy_id="policy:v1",
        eligible=False,
        rationale=None,
    )

    for value in record.__dict__.values():
        # bool is allowed; numeric magnitudes are not
        if isinstance(value, bool):
            continue

        assert not isinstance(
            value, (int, float)
        ), f"Numeric magnitude leaked into eligibility record: {value!r}"
