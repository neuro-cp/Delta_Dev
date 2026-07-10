# RC3 State Model

RC3 is the governed objective layer above the frozen RC2 cognitive pipeline.
RC2 answers a turn. RC3 evaluates explicit objectives over time.

This document is the state contract for RC3. It defines the objects that future
goal, planning, introspection, progress, controlled forgetting, plugin,
sandbox, proposal, and project systems must use before adding behavior.

RC3 state is ephemeral by default. Nothing in this model enables autonomous
action, hidden persistence, plugin execution, provider calls, canonical writes,
graph writes, replay writes, scheduler activation, commits, pushes, deployment,
or self-modification.

## Architecture Boundary

RC2 answers:

```text
How should this turn be understood and answered?
```

RC3 evaluates:

```text
What explicit objective is being pursued, what plan represents it, and what
evidence shows progress?
```

RC3 must not replace RC2 turn-level cognition. It consumes RC2 output as
evidence and context.

## State Hierarchy

```text
RC2 CognitiveEpisode
        |
        v
RC3Episode
        |-- GoalFrame
        |-- PlanFrame
        |-- GoalPlanArbitration
        |-- IntrospectionSnapshot
        |-- ProgressEvaluation
        `-- CapabilityGapAssessment
```

## Global State Rules

All RC3 objects must be:

- ephemeral by default
- read-only with respect to production state
- serializable
- inspectable in Developer Overlay
- provenance-aware
- explicit about authority
- explicit about persistence status
- explicit about safety flags
- reversible at the code level

RC3 objects must not:

- create hidden goals
- execute plans
- use providers automatically
- write substrate memory
- create graph edges
- create replay records
- activate plugins
- create sandboxes
- commit, push, merge, deploy, or mutate production
- interact with DELTA-75

## Object: GoalFrame

Purpose: represent an explicit operator objective or constraint.

Owner: RC3 goal layer.

Creation trigger: an explicit user objective, prohibition, success condition,
preference, or clarification need.

Lifecycle: `proposed -> interpreted -> awaiting_clarification -> confirmed ->
active -> paused -> blocked -> completed -> abandoned -> superseded ->
rejected`.

Allowed readers: RC3 planning, arbitration, introspection, progress evaluation,
Developer Overlay.

Allowed writers: current turn construction only. Future persistence requires a
separate operator-approved project-memory protocol.

Persistence status: `ephemeral`.

Mutation authority: none after construction inside this milestone.

Provenance requirements: source user text, creation turn, extraction rule or
operator confirmation status, confidence, uncertainty.

Rollback behavior: discard the frame. No durable rollback is needed unless a
future persistence layer stores it.

Serialization format: JSON object with stable scalar fields and list fields.

Developer Overlay representation: objective, type, explicitness, constraints,
prohibitions, assumptions, dependencies, confidence, uncertainty, persistence
status.

Safety fields: no training, provider call, memory write, graph write, replay
write, action, scheduler, commit, push, deployment, plugin activation, or
DELTA-75 interaction.

Relationships: may produce a PlanFrame; may be referenced by
GoalPlanArbitration, ProgressEvaluation, and CapabilityGapAssessment.

Relationship to RC2 CognitiveEpisode: RC2 provides the interpreted user turn;
RC3 decides whether that turn contains an explicit objective.

Operator approval required: not for ephemeral interpretation; required for
future persistence or execution-adjacent workflows.

## Object: PlanFrame

Purpose: describe a non-executing plan for a GoalFrame.

Owner: RC3 planning layer.

Creation trigger: a confirmed or sufficiently explicit GoalFrame.

Lifecycle: `draft -> reviewable -> needs_revision -> operator_revised ->
blocked -> superseded -> retired`.

Allowed readers: arbitration, introspection, progress evaluation,
capability-gap analysis, Developer Overlay.

Allowed writers: current turn construction only. Revision requires a bounded
operator-reviewed revision protocol in later RC3 work.

Persistence status: `ephemeral`.

Mutation authority: none after construction inside this milestone.

Provenance requirements: goal ID, source constraints, assumptions, dependency
notes, risk notes, evidence references, plan construction rule.

Rollback behavior: discard the frame or supersede it with an explicitly linked
replacement.

Serialization format: JSON object containing ordered read-only plan steps.

Developer Overlay representation: strategy, steps, dependencies, constraints
preserved, prohibited actions, risks, uncertainty, non-execution flag.

Safety fields: plan execution false, tool execution false, plugin activation
false, sandbox creation false, commit false, push false.

Relationships: belongs to one GoalFrame; is evaluated by ProgressEvaluation;
may request CapabilityGapAssessment.

Relationship to RC2 CognitiveEpisode: RC2 may answer a planning question; RC3
PlanFrame is the inspectable objective-level representation of that plan.

Operator approval required: not for read-only planning; required before any
future revision persistence, sandbox work, or integration.

## Object: GoalPlanArbitration

Purpose: decide whether the goal and plan are coherent, constrained, and
allowed.

Owner: RC3 arbitration layer.

Creation trigger: GoalFrame and PlanFrame both exist.

Lifecycle: `candidate -> accepted -> rejected -> needs_clarification`.

Allowed readers: Developer Overlay, progress evaluation, proposal systems.

Allowed writers: current turn construction only.

Persistence status: `ephemeral`.

Mutation authority: none.

Provenance requirements: selected goal ID, selected plan ID, rejected reasons,
conflict notes, constraint checks.

Rollback behavior: discard arbitration result.

Serialization format: JSON object containing status, conflicts, and decision
reason.

Developer Overlay representation: selected goal, selected plan, rejected
alternatives, safety blockers, unresolved questions.

Safety fields: execution authorized false, self-approval false, production
mutation false.

Relationships: binds GoalFrame to PlanFrame.

Relationship to RC2 CognitiveEpisode: separate from RC2 route arbitration; RC2
chooses how to answer a turn, RC3 chooses whether a goal and plan are valid.

Operator approval required: required before any action-adjacent transition.

## Object: IntrospectionSnapshot

Purpose: report evidence-based state about the current RC3 episode and known
runtime boundaries.

Owner: RC3 introspection layer.

Creation trigger: explicit introspection request or RC3 episode generation.

Lifecycle: `observed -> reported -> expired`.

Allowed readers: Developer Overlay, operator UI, progress evaluation.

Allowed writers: current turn construction only.

Persistence status: `ephemeral`.

Mutation authority: none.

Provenance requirements: every self-state claim must cite observable state or a
named report/document.

Rollback behavior: discard snapshot.

Serialization format: JSON object with claim/evidence pairs and uncertainty.

Developer Overlay representation: capability claims, limitation claims,
assumptions, uncertainty, evidence references.

Safety fields: fabricated self-state false; hidden state false.

Relationships: may inspect GoalFrame, PlanFrame, arbitration, and progress
state.

Relationship to RC2 CognitiveEpisode: RC2 may provide answer content; RC3
introspection reports objective-layer state only.

Operator approval required: no for read-only reporting.

## Object: ProgressEvaluation

Purpose: assess whether evidence supports progress, completion, blockage, or
failure.

Owner: RC3 progress layer.

Creation trigger: plan exists or operator asks for progress.

Lifecycle: `not_started -> in_progress -> blocked -> needs_evidence ->
completed -> failed -> abandoned`.

Allowed readers: goal layer, planning layer, Developer Overlay.

Allowed writers: current turn construction only.

Persistence status: `ephemeral`.

Mutation authority: none.

Provenance requirements: completion evidence, missing evidence, failure
evidence, regression evidence.

Rollback behavior: discard evaluation.

Serialization format: JSON object with status, score, evidence, and missing
evidence.

Developer Overlay representation: status, completion score, evidence, missing
evidence, blockers.

Safety fields: no completion without evidence, no hidden progress state.

Relationships: evaluates a PlanFrame for a GoalFrame.

Relationship to RC2 CognitiveEpisode: RC2 can answer progress questions; RC3
records the evidence boundary.

Operator approval required: required before durable project status updates.

## Object: CapabilityGapAssessment

Purpose: determine whether a goal can be satisfied by existing capabilities or
requires a proposal for new capability.

Owner: RC3 capability layer.

Creation trigger: a PlanFrame references a capability, plugin, tool, sandbox,
or external operation.

Lifecycle: `observed -> matched_existing_capability -> gap_identified ->
proposal_needed -> blocked`.

Allowed readers: planning, proposal system, plugin registry, Developer Overlay.

Allowed writers: current turn construction only.

Persistence status: `ephemeral`.

Mutation authority: none.

Provenance requirements: requested capability, existing capability candidates,
unsupported requirement, recommended next step.

Rollback behavior: discard assessment.

Serialization format: JSON object with capability requested, matches, gaps,
and recommendation.

Developer Overlay representation: existing capability found, missing
capability, plugin needed, sandbox needed, proposal needed.

Safety fields: plugin activation false, sandbox creation false, tool execution
false.

Relationships: may be derived from GoalFrame and PlanFrame; may later feed
Proposal.

Relationship to RC2 CognitiveEpisode: RC2 may answer capability questions; RC3
decides whether the objective needs new capability.

Operator approval required: required before plugin activation, sandbox work,
or proposal integration.

## Object: RC3Episode

Purpose: bundle all RC3 state for one governed objective interpretation cycle.

Owner: RC3 orchestration layer.

Creation trigger: explicit RC3 invocation or future goal/planning mode.

Lifecycle: `created -> evaluated -> reported -> expired`.

Allowed readers: Developer Overlay, operator UI, report generators.

Allowed writers: current construction path only.

Persistence status: `ephemeral`.

Mutation authority: none.

Provenance requirements: source text, creation timestamp, RC2 episode
reference when available, generated object IDs, safety flags.

Rollback behavior: discard episode.

Serialization format: JSON object containing nested RC3 objects.

Developer Overlay representation: top-level RC3 trace with links to goal,
plan, arbitration, introspection, progress, and capability gap sections.

Safety fields: full invariant set from RC2 plus RC3-specific false values for
execution, tool use, plugin activation, sandbox creation, commit, push,
deployment, and production mutation.

Relationships: contains the other RC3 objects.

Relationship to RC2 CognitiveEpisode: references RC2 but does not replace it.

Operator approval required: no for ephemeral construction; yes for persistence,
sandboxing, integration, plugin activation, or any durable workflow.

## Four-Milestone Organization

The 24-phase RC3 roadmap should be implemented through four large checkpoints:

1. RC3 Foundation: goals, plans, arbitration, introspection, progress
   evaluation, capability-gap assessment. No execution, plugins, sandboxes, or
   persistence.
2. RC3 Engineering: plugin contracts, coding capability, sandbox runtime,
   proposal generation. No integration.
3. RC3 Governance: external review, operator approval, controlled merge,
   plugin activation, rollback.
4. RC3 Long Horizon: persistent project state, long-running plans, controlled
   forgetting, multi-session execution, operator pilot, freeze.

## Capability Gap Rule

RC3 must not jump directly from a plan to new code.

Required sequence:

```text
Goal
-> Plan
-> Capability Gap Assessment
-> Existing capability?
-> If yes: recommend governed use
-> If no: proposal for new capability
-> Sandbox only after review
```

This prevents DELTA from reinventing existing functionality and keeps
engineering work evidence-based.

## Non-Negotiable Boundary

Allowed future path:

```text
Goal
-> Plan
-> Introspection
-> Capability gap
-> Sandbox experiment
-> Evidence
-> Proposal
-> External review
-> Operator approval
-> Controlled integration
```

Forbidden path:

```text
Goal
-> Self-authorized action
-> Production mutation
```
