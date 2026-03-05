"""
Phase-15 scope for semantic → assembly hypotheses.

This file defines what *may be referenced* by hypotheses.
"""

# Regions allowed must be a subset of Phase-14 grounding.
ALLOWED_REGIONS = {
    "pfc",
    "association_cortex",
    "hip_base",
    "amyg_base",
    "pulvinar",
}

# Assemblies are referenced symbolically.
# No validation against runtime or loader is permitted here.
#
# Assembly identifiers are opaque strings.
# Interpretation is explicitly out of scope.
