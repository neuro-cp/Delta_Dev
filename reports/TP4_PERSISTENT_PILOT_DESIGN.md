# TP4 Persistent Pilot Design

- pilot_name: TP5 controlled noncanonical persistent pilot
- selected_capability: `operator_reviewed_noncanonical_semantic_consolidation_from_real_operator_sessions`
- enabled_now: `False`
- target_store: `data/tp5_noncanonical_pilot_store/`
- canonical: `False`

## Architecture

- operator session input
- candidate semantic extraction into staging
- review bundle with provenance and uncertainty
- strict operator approval
- isolated noncanonical persistent store write
- audit event
- rollback token
- read-only evaluation replay

## Abort Criteria

- any provider call
- any canonical write
- any memory/knowledge mutation outside isolated pilot store
- any scheduler/background worker
- any action execution
- any hidden approval inference
- any secret exposure