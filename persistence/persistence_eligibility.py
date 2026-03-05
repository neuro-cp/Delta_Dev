from memory.episodic.reset_eligibility import ResetEligibility

# Persistence is intentionally NOT episode-aware.
# It represents long-horizon bias and must survive episode boundaries.
PERSISTENCE_RESET_ELIGIBILITY = ResetEligibility.NEVER
