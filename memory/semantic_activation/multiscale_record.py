from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class MultiscaleActivationRecord:
    """
    Immutable snapshot of semantic activation across multiple timescales.

    Descriptive only.
    No authority.
    Safe to discard and recompute.
    """

    # scale_name -> (ontology_term -> activation)
    activations_by_scale: Dict[str, Dict[str, float]]

    # snapshot index shared across scales
    snapshot_index: int
