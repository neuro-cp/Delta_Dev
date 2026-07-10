# RC3 Operator Pilot And Freeze Protocol

RC3 must build above the frozen RC2 cognitive pipeline. It must not turn goals into self-authorized production mutation.

The governing shape is:

```text
Goal
-> Plan
-> Introspection
-> Sandbox experiment
-> Evidence
-> Proposal
-> External review
-> Operator approval
-> Controlled integration
```

The forbidden shape is:

```text
Goal
-> Self-authorized action
-> Production mutation
```

## Release Milestones

- RC3-A - Goal and Planning Scaffold: goals, plans, introspection, progress evaluation; no execution
- RC3-B - Governed Plan Revision: monitoring, self-evaluation, revision, controlled forgetting; no production action
- RC3-C - Plugin Architecture: plugin manifests, capability registry, permissions, operator activation
- RC3-D - Sandbox Engineering: coding plugin, sandbox runtime, test-observe-revise loop, proposal generation
- RC3-E - External Review and Integration: review export/import, operator approval, controlled integration, rollback
- RC3-F - Long-Horizon Project Cognition: persistent project goals, multi-session plans, resume behavior, dashboards
- RC3-G - Adversarial Pilot and Freeze: red-team evaluation, operator pilot, full benchmark, freeze review

## Four Major Checkpoints

The 24 phases should be implemented through four larger checkpoints rather
than as a mechanically linear sequence:

- RC3 Foundation: goals, plans, arbitration, introspection, progress
  evaluation, capability-gap assessment. No execution, plugins, sandboxes, or
  persistence.
- RC3 Engineering: plugin contracts, coding capability, sandbox runtime, and
  proposal generation. Still no integration.
- RC3 Governance: external review, operator approval, controlled merge, plugin
  activation, and rollback.
- RC3 Long Horizon: persistent project state, long-running plans, controlled
  forgetting, multi-session execution, operator pilot, and freeze.

The state model for these checkpoints is defined in
`docs/RC3_STATE_MODEL.md`.

## Phase Order

- Phase 0 - Foundation Lock (RC3-A): Freeze RC2 as the stable answer-this-turn substrate.
- Phase 1 - Goals (RC3-A): Extract explicit operator goals without hidden goals.
- Phase 2 - Planning (RC3-A): Create non-executing plans that preserve constraints.
- Phase 3 - Goal / Plan Arbitration (RC3-A): Resolve conflicts between goals, constraints, and plans.
- Phase 4 - Introspection (RC3-A): Report evidence-based runtime state without fabricating self-state.
- Phase 5 - Progress Evaluation (RC3-A): Assess completion using evidence rather than intention.
- Phase 6 - Plan Revision (RC3-B): Revise plans in bounded ways when evidence changes.
- Phase 7 - Controlled Forgetting (RC3-B): Design reversible deactivation, quarantine, and curriculum exclusion.
- Phase 8 - Plugin Contract (RC3-C): Define plugin manifests, permissions, tests, and rollback.
- Phase 9 - Coding Capability (RC3-D): Generate code proposals in isolation.
- Phase 10 - Sandbox Runtime (RC3-D): Run experiments outside production.
- Phase 11 - Experimental Revision Loop (RC3-D): Iterate code/tests inside the sandbox.
- Phase 12 - Proposal System (RC3-D): Package objective, diff, validation, risks, and rollback.
- Phase 13 - External Review (RC3-E): Export proposal for independent review and import review feedback.
- Phase 14 - Controlled Integration (RC3-E): Apply operator-approved changes only through governed integration.
- Phase 15 - Plugin Activation (RC3-E): Activate plugins only after permission and rollback checks.
- Phase 16 - Goal-Driven Plugin Selection (RC3-E): Recommend plugins from goals without activating them.
- Phase 17 - Persistent Project Memory (RC3-F): Persist project goals and decisions under governance.
- Phase 18 - Long-Horizon Execution (RC3-F): Continue governed projects across sessions.
- Phase 19 - Adversarial Safety Evaluation (RC3-G): Stress permissions, self-approval, persistence, and rollback.
- Phase 20 - RC3 Benchmark Suite (RC3-G): Measure goals, plans, introspection, plugins, sandboxes, and RC2 preservation.
- Phase 21 - Operator Console (RC3-G): Expose project, goal, plugin, sandbox, and proposal state.
- Phase 22 - Real Operator Pilot (RC3-G): Test controlled real projects without autonomy.
- Phase 23 - RC3 Freeze Readiness (RC3-G): Decide whether RC3 is stable enough to freeze.

## Real Operator Pilot

- 1. Read-only goal interpretation: Extract the operator's explicit objective and constraints. (read-only; no production mutation)
- 2. Read-only planning: Produce a non-executing plan. (read-only; no production mutation)
- 3. Operator-reviewed plan revision: Revise plan after operator feedback. (operator-reviewed; no production mutation)
- 4. Sandbox coding task: Run code work in an isolated sandbox only. (operator-reviewed; no production mutation)
- 5. Proposal generation: Package changes, evidence, risks, and rollback. (read-only; no production mutation)
- 6. External review: Export proposal for independent review. (operator-reviewed; no production mutation)
- 7. Operator-approved integration: Integrate only after explicit operator approval. (operator-reviewed; no production mutation)
- 8. Plugin activation: Activate plugin only through explicit approval. (operator-reviewed; no production mutation)
- 9. Multi-session project continuation: Resume project state with visible context. (operator-reviewed; no production mutation)
- 10. Controlled forgetting test: Quarantine/deactivate under governance. (operator-reviewed; no production mutation)
- 11. Rollback test: Prove proposal/plugin/project rollback. (operator-reviewed; no production mutation)
- 12. Emergency disable test: Disable RC3 extensions without harming RC2. (operator-reviewed; no production mutation)

## Controlled Forgetting Boundary

Controlled forgetting belongs in RC3 design but is not enabled by this protocol. It must preserve provenance, operator reason, affected records, rollback or recovery path, benchmark impact, and Developer Overlay visibility.

Valid future forms include working-memory expiration, concept quarantine, concept deprecation, edge deactivation, curriculum exclusion, and operator-approved noncanonical cleanup.

## Freeze Gate

RC3 is not freeze-ready until all freeze criteria have implementation evidence, RC2 preservation gates pass, rollback is verified, and a stable checkpoint is operator-approved.

Current recommendation: `READY_TO_BEGIN_RC3_A_GOAL_AND_PLANNING_SCAFFOLD`
Current freeze recommendation: `NOT_READY_FOR_RC3_FREEZE_IMPLEMENT_RC3_A_THROUGH_RC3_G_FIRST`
