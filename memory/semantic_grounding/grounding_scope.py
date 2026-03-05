"""
Phase 14 grounding scope.

This file defines the ONLY regions that semantic grounding
is allowed to reference in Phase 14.

Any expansion of this set requires an explicit scope revision.
"""

# --------------------------------------------------
# Canonical Phase-14 Grounding Seed (v1)
# --------------------------------------------------

# NOTE:
# These are region *identifiers*, not functional claims.
# Presence here does NOT imply influence, importance, or activation.

ALLOWED_GROUNDING_REGIONS = {
    "pfc",
    "association_cortex",
    "hip_base",
    "amyg_base",
    "pulvinar",
}

# --------------------------------------------------
# Explicitly excluded (documented for clarity)
# --------------------------------------------------

# The following are intentionally NOT allowed here:
#
# - striatum, gpi, gpe, stn
# - vta, snc, locus_coeruleus, raphe
# - trn
# - sensory_input regions
# - primary sensory cortices (v1, a1, s1)
# - motor cortex (m1)
# - cerebellum
# - hypothalamic nuclei
#
# Grounding to any of these requires reopening Phase 14.
