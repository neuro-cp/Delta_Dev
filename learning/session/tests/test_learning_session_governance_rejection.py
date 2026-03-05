# learning/session/tests/test_learning_session_governance_rejection.py

import pytest

from learning.session.learning_session import LearningSession
import learning.session.learning_session as session_module


def test_learning_session_hard_fails_on_governance_rejection(monkeypatch):
    """
    Proves that governance rejection aborts LearningSession.run().

    This patches the governance function at the usage site
    inside learning_session.py, not at its definition site.
    """

    session = LearningSession(replay_id="r1")

    def force_reject(*args, **kwargs):
        raise AssertionError("GovernanceGate rejected learning session.")

    # Patch the symbol where LearningSession actually calls it
    monkeypatch.setattr(
        session_module,
        "run_governance_chain",
        force_reject,
    )

    with pytest.raises(AssertionError):
        session.run(inputs=[])