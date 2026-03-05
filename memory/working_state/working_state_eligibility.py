from memory.episodic.reset_eligibility import ResetEligibility

# Working state MAY acknowledge episode boundaries,
# but MUST NOT reset or disengage without an explicit policy.
WORKING_STATE_RESET_ELIGIBILITY = ResetEligibility.ELIGIBLE
