from __future__ import annotations

from memory.proposal_channels.proposal_record import ProposalRecord


def test_proposal_record_is_immutable() -> None:
    record = ProposalRecord(
        proposal_id="prop:1",
        source_artifact_id="artifact:1",
        source_artifact_type="semantic_grounding",
        proposed_target="pfc",
        proposal_channel_id="channel:v1",
        rationale=None,
    )

    try:
        record.proposed_target = "v1"  # type: ignore[misc]
        mutated = True
    except Exception:
        mutated = False

    assert mutated is False


def test_proposal_record_has_no_numeric_magnitudes() -> None:
    record = ProposalRecord(
        proposal_id="prop:1",
        source_artifact_id="artifact:1",
        source_artifact_type="semantic_grounding",
        proposed_target="pfc",
        proposal_channel_id="channel:v1",
        rationale=None,
    )

    for value in record.__dict__.values():
        if isinstance(value, bool):
            continue

        assert not isinstance(
            value, (int, float)
        ), f"Numeric magnitude leaked into proposal record: {value!r}"
