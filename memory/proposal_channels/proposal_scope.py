"""
Defines what MAY generate proposals.
"""

ALLOWED_PROPOSAL_SOURCES = {
    "semantic_grounding",
    "semantic_assembly_hypothesis",
    "semantic_activation_summary",
}

# Explicitly excluded:
#
# - runtime state
# - decision state
# - salience
# - value
# - routing
# - learning
