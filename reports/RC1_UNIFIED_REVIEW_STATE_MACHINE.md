# RC1 Unified Proposal Review State Machine

Lifecycle: `unified-review-lifecycle-a8c6c8ab850a92f3`
Current state: `integrated_disabled`

## Transitions

- draft -> review: proposal_created_for_human_review (allowed=True, live_write=False)
- review -> admin_approved: explicit_admin_review_state_present (allowed=True, live_write=False)
- admin_approved -> overwatch_allowed: local_overwatch_simulation_allows_review_continuation (allowed=True, live_write=False)
- overwatch_allowed -> simulation_ready: knowledge_evolution_candidate_built (allowed=True, live_write=False)
- simulation_ready -> ready_to_integrate: impact_and_rollback_are_available (allowed=True, live_write=False)
- ready_to_integrate -> integrated_disabled: live_integration_gate_remains_closed (allowed=False, live_write=False)
- integrated_disabled -> rolled_back_available: rollback_reference_remains_available (allowed=True, live_write=False)

## Safety

- integration_write_performed: False
- knowledge_mutation_performed: False
- memory_mutation_performed: False
- provider_call_performed: False
- rollback_available: True
- training_performed: False

## Final Recommendation

PROCEED_CENTRAL_RUNTIME_ARTIFACT_REGISTRY
