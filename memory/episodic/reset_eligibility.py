from __future__ import annotations

from enum import Enum, auto


class ResetEligibility(Enum):
    """
    Declarative eligibility for acknowledging episode boundaries.

    This enum is a *contract*, not a mechanism.

    It answers ONLY:
      - Is this subsystem allowed to notice that an episode ended?

    It does NOT:
      - trigger resets
      - enforce behavior
      - imply decay, clearing, or learning
      - introduce callbacks or hooks

    Any subsystem not explicitly marked MUST behave as if
    episode boundaries do not exist.
    """

    # --------------------------------------------------
    # A — Episode-agnostic (never acknowledge boundaries)
    # --------------------------------------------------
    NEVER = auto()
    """
    The subsystem is temporally continuous.

    Episode boundaries are irrelevant and must not influence
    state, dynamics, thresholds, or behavior.

    Examples:
      - Population dynamics
      - Competition kernels
      - Decision latch thresholds
      - Structural routing
    """

    # --------------------------------------------------
    # B — Boundary-aware (eligibility only, no action)
    # --------------------------------------------------
    ELIGIBLE = auto()
    """
    The subsystem may acknowledge that an episode boundary occurred,
    but MUST NOT act on it without an explicit policy.

    This category exists to allow *future* reset, decay,
    or reinitialization mechanisms without architectural violation.

    Examples:
      - Working memory buffers
      - Context gain fields
      - Salience traces
      - Persistence counters
    """

    # --------------------------------------------------
    # C — Episode-native (must acknowledge boundaries)
    # --------------------------------------------------
    REQUIRED = auto()
    """
    The subsystem exists specifically because episodes exist.

    Episode boundaries are semantically meaningful and required
    for correctness, but still carry no execution authority.

    Examples:
      - Episodic trace
      - Episode trackers
      - Replay / consolidation systems
      - Offline analysis
    """
