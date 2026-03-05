# learning/session/tests/test_governance_chain_sensitivity.py

from learning.session._governance_flow import run_governance_chain


# --------------------------------------------------
# Surfaces aligned with FragilityPolicy contract
# --------------------------------------------------

class CleanSurface:
    coherence = {"coherence_index": 1}
    entropy = {"entropy_index": 0}
    momentum = {"momentum_index": 0}
    escalation = {"pressure": 0}


class SlightlyFragileSurface:
    coherence = {"coherence_index": 0}
    entropy = {"entropy_index": 1}
    momentum = {"momentum_index": 0}
    escalation = {"pressure": 0}


class HighlyFragileSurface:
    coherence = {"coherence_index": 0}
    entropy = {"entropy_index": 5}
    momentum = {"momentum_index": 5}
    escalation = {"pressure": 5}


# --------------------------------------------------
# Minimal proposal stub
# --------------------------------------------------

class DummyProposal:
    def __init__(self, delta_count: int):
        self.deltas = [object() for _ in range(delta_count)]


# --------------------------------------------------
# Sensitivity + determinism test
# --------------------------------------------------

def test_governance_chain_is_sensitive_and_deterministic():
    proposals = [DummyProposal(delta_count=2)]

    # --- Clean baseline ---
    record_clean_a = run_governance_chain(
        proposals=proposals,
        report_surface=CleanSurface(),
    )

    record_clean_b = run_governance_chain(
        proposals=proposals,
        report_surface=CleanSurface(),
    )

    # Determinism check
    assert record_clean_a == record_clean_b

    # --- Slight fragility must reject ---
    slight_rejected = False
    try:
        run_governance_chain(
            proposals=proposals,
            report_surface=SlightlyFragileSurface(),
        )
    except AssertionError:
        slight_rejected = True

    assert slight_rejected is True

    # --- High fragility must reject ---
    high_rejected = False
    try:
        run_governance_chain(
            proposals=proposals,
            report_surface=HighlyFragileSurface(),
        )
    except AssertionError:
        high_rejected = True

    assert high_rejected is True