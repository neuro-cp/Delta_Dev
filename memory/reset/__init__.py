from __future__ import annotations

"""
Phase 6C — Reset Arbitration Guard Tests

This test suite is intentionally observational.
It proves that reset arbitration NEVER authorizes a reset,
regardless of subsystem eligibility signals.

No runtime.
No hooks.
No execution.
"""

from dataclasses import dataclass
from typing import Dict, Any


# --------------------------------------------------
# Mock state objects (minimal, read-only)
# --------------------------------------------------

@dataclass
class MockDecisionState:
    active: bool


@dataclass
class MockControlState:
    committed: bool
    suppress_alternatives: bool
    working_state_active: bool


# --------------------------------------------------
# Reset arbitration stub (design-locked)
# --------------------------------------------------

def arbitrate_reset(
    *,
    decision_state: MockDecisionState,
    control_state: MockControlState,
    eligibility: Dict[str, bool],
) -> bool:
    """
    Reset arbitration v0.

    This mirrors reset_arbitration_policy.md:
    - Guard layers veto everything
    - No authorization is possible in v0
    """

    # --- Decision guard ---
    if decision_state.active:
        return False

    # --- Control guard ---
    if (
        control_state.committed
        or control_state.suppress_alternatives
        or control_state.working_state_active
    ):
        return False

    # --- Arbitration phase (v0 default) ---
    # Even if eligibility exists, v0 authorizes nothing.
    return False


# --------------------------------------------------
# Tests
# --------------------------------------------------

def test_reset_denied_when_decision_active() -> None:
    decision = MockDecisionState(active=True)
    control = MockControlState(
        committed=False,
        suppress_alternatives=False,
        working_state_active=False,
    )

    eligibility = {
        "episodic": True,
        "context": True,
        "salience": True,
    }

    authorized = arbitrate_reset(
        decision_state=decision,
        control_state=control,
        eligibility=eligibility,
    )

    assert authorized is False


def test_reset_denied_when_control_committed() -> None:
    decision = MockDecisionState(active=False)
    control = MockControlState(
        committed=True,
        suppress_alternatives=True,
        working_state_active=True,
    )

    eligibility = {
        "episodic": True,
        "context": True,
        "salience": True,
    }

    authorized = arbitrate_reset(
        decision_state=decision,
        control_state=control,
        eligibility=eligibility,
    )

    assert authorized is False


def test_reset_denied_even_when_all_eligibility_true() -> None:
    decision = MockDecisionState(active=False)
    control = MockControlState(
        committed=False,
        suppress_alternatives=False,
        working_state_active=False,
    )

    eligibility = {
        "episodic": True,
        "context": True,
        "salience": True,
        "working_state": True,
    }

    authorized = arbitrate_reset(
        decision_state=decision,
        control_state=control,
        eligibility=eligibility,
    )

    assert authorized is False


def test_reset_denied_when_no_eligibility() -> None:
    decision = MockDecisionState(active=False)
    control = MockControlState(
        committed=False,
        suppress_alternatives=False,
        working_state_active=False,
    )

    eligibility = {}

    authorized = arbitrate_reset(
        decision_state=decision,
        control_state=control,
        eligibility=eligibility,
    )

    assert authorized is False
