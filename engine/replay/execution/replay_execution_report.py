from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass(frozen=True)
class ReplayExecutionReport:
    """
    Inspection artifact for replay execution.

    This report answers:
    - What replay was executed?
    - In what order?
    - What cognition outputs were produced?

    NOTE:
    Cognition outputs are treated as OPAQUE.
    This module must not depend on cognition internals.
    """

    # Reason carried from ReplayRequest (human/system readable)
    replay_request_reason: str

    # Ordered episode IDs actually replayed
    executed_episode_ids: List[str]

    # Opaque cognition output (e.g. hypothesis timeline)
    cognition_output: Any

    # Diagnostics
    observation_frame_count: int

    # --------------------------------------------------
    # Optional contextual metadata (inspection only)
    # --------------------------------------------------

    # Sleep profile that initiated this replay (if any)
    sleep_profile: Optional[str] = None

    # Origin of replay request (e.g. "sleep_orchestrator", "manual")
    origin: Optional[str] = None
