from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class ObservationFrame:
    """
    Read-only offline observation frame for hypothesis processing.

    This object:
    - is immutable
    - carries no authority
    - contains no runtime references
    - is safe to store, replay, and audit

    Semantics:
    - step: discrete timestep index
    - salience: optional scalar salience value (already reduced)
    - assembly_outputs: optional named scalar observations
      (e.g. population or region outputs, already flattened)
    - semantic_activation: optional descriptive semantic mass snapshot
      (offline, non-authoritative)
    """

    step: int
    salience: Optional[float] = None
    assembly_outputs: Optional[Dict[str, float]] = None
    semantic_activation: Optional[Dict[str, float]] = None
