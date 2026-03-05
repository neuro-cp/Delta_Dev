from __future__ import annotations

from memory.semantic_grounding.grounding_scope import (
    ALLOWED_GROUNDING_REGIONS,
)


def test_grounding_scope_contains_only_seed_regions() -> None:
    assert ALLOWED_GROUNDING_REGIONS == {
        "pfc",
        "association_cortex",
        "hip_base",
        "amyg_base",
        "pulvinar",
    }


def test_grounding_scope_excludes_decision_and_modulation_regions() -> None:
    forbidden = {
        "striatum",
        "gpi",
        "gpe",
        "stn",
        "vta",
        "snc",
        "trn",
        "v1",
        "a1",
        "s1",
        "m1",
        "hypothalamus",
    }

    assert ALLOWED_GROUNDING_REGIONS.isdisjoint(forbidden)
