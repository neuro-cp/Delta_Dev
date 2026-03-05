# learning/session/tests/test_learning_session_governance_integration.py

from learning.session._governance_flow import run_governance_chain
from learning.schemas.learning_proposal import LearningProposal
from learning.schemas.learning_delta import LearningDelta


class CleanSurface:
    coherence = {}
    entropy = {}
    momentum = {}
    escalation = {}


class FragileSurface:
    coherence = {"x": 10.0}
    entropy = {"x": 10.0}
    momentum = {"x": 10.0}
    escalation = {"x": 10.0}


def _make_proposal(delta_count: int):
    deltas = [
        LearningDelta(
            target=f"t{i}",
            delta_type="additive",
            magnitude=1.0,
            metadata={},
        )
        for i in range(delta_count)
    ]

    return LearningProposal(
        proposal_id="p1",
        source_replay_id="r1",
        deltas=deltas,
        confidence=1.0,
        justification={"reason": "test"},
        bounded=True,
        replay_consistent=True,
        audit_tags=[],
    )


def test_governance_passes_when_clean():
    proposals = [_make_proposal(1)]
    surface = CleanSurface()

    record = run_governance_chain(proposals, surface)

    assert record is not None


def test_governance_rejects_when_fragile():
    proposals = [_make_proposal(1)]
    surface = FragileSurface()

    try:
        run_governance_chain(proposals, surface)
        assert False, "Expected governance rejection."
    except AssertionError:
        assert True