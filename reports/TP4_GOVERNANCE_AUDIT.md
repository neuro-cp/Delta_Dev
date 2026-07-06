# TP4 Governance Audit

- all_required_layers_present: `True`
- no_instrumentation_patch_required_now: `True`

- provenance: strong
- operator_approval: strong
- rollback: strong_for_isolated_store
- audit_trail: strong
- deterministic_replay: strong
- safety_gates: strong
- refusal_behavior: strong
- contradiction_preservation: strong
- uncertainty_handling: strong
- invariant_enforcement: strong

## Weak Points

- rollback execution must stay manual/workspace-scoped in TP5
- real operator-session documents may expose malformed provenance edge cases
- exact approval parser must reject casual approval phrases