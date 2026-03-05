"""
Phase-16 eligibility scope.

Defines which artifact classes may ever be evaluated
for influence eligibility.
"""

ELIGIBLE_ARTIFACT_TYPES = {
    "semantic_grounding",
    "semantic_assembly_hypothesis",
    "semantic_activation_summary",
    "inspection_diff",
}

# Explicitly excluded:
#
# - runtime state
# - decisions
# - value signals
# - salience signals
# - routing influence
# - learning deltas
