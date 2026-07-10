# RC3 Plan Revision Contract

RC3-B answers one question:

```text
Should the existing read-only plan change?
```

It does not execute the revised plan.

## Supported Revision Triggers

- user changes objective
- clarification received
- assumption invalidated
- prerequisite unavailable
- dependency failure
- operator correction
- evidence update
- capability change
- safety restriction
- scope reduction
- scope expansion
- conflicting goal
- higher-priority goal

Unsupported triggers are rejected. Supported triggers without justification are
also rejected.

## Required Revision Artifacts

Every accepted revision must include:

- revision cause
- evidence used
- assumptions changed
- constraints affected
- risks introduced
- risks removed
- confidence
- uncertainty
- plan diff
- validation result
- ephemeral revision history
- monitoring diagnostics
- self-evaluation
- controlled-forgetting hooks

## Authority Boundary

RC3-B may revise a `PlanFrame`. It may not execute it, persist it, activate a
plugin, create a sandbox, call providers, write memory, create graph or replay
records, commit, push, deploy, or touch DELTA-75.

## Controlled Forgetting Hooks

RC3-B only defines placeholders for future forgetting:

- obsolete assumptions
- superseded revisions
- abandoned plans
- archived alternatives

The hooks do not delete or persist anything.
