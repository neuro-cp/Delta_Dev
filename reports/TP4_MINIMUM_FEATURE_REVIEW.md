# TP4 Minimum Feature Review

- selected_capability: `operator_reviewed_noncanonical_semantic_consolidation_from_real_operator_sessions`
- recommended_activation_state: `design_ready_not_enabled`
- explicitly_not_activated: `True`

## Why Safe

- operator-reviewed
- reversible
- provenance-backed
- deterministic
- audit logged
- feature-scoped
- experimentally measurable

## Rejected Candidates

- provider_assisted_evidence: provider calls remain prohibited and would add authority/secret risk
- canonical_memory_writes: canonical writes are too permanent for the first persistent pilot
- autonomous_action_execution: execution side effects are unrelated to validating substrate persistence
- HYB1 promotion: variant promotion would confound the Model B baseline