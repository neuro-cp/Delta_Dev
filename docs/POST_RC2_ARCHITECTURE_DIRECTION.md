# Post-RC2 Architecture Direction

This document records the long-term direction after RC2 reaches refinement
freeze. It is not an implementation request and it does not change the RC2
runtime.

RC2 answers one turn well. RC3 and later phases should build above that stable
pipeline instead of continuing to add new machinery inside it.

## Current Position

DELTA has matured from a collection of cognitive modules into a governed
cognitive runtime. The core should remain small, stable, inspectable, and
highly governed.

The RC2 core remains responsible for:

- conversation
- dialogue intent and communication-act classification
- route candidate generation
- route arbitration
- working memory reference resolution
- Working Reasoning Set behavior
- contradiction analysis
- analogy analysis
- abstraction
- substrate recall
- natural conversation rendering
- Developer Overlay traces
- safety normalization
- governance boundaries

Future capability growth should occur through controlled extension, not by
turning the core into a monolithic system that contains every future
capability.

## Long-Term Direction

The next major architectural evolution is not autonomous self-modification.

The direction is operator-governed recursive engineering: DELTA should
eventually understand enough of its own architecture to help engineer
improvements under human supervision.

This means DELTA may eventually help:

- identify narrowly scoped capability gaps
- understand module boundaries and architectural contracts
- propose changes
- write code in isolation
- compile and test safely
- evaluate benchmark impact
- package evidence
- request operator approval

It does not mean DELTA may:

- edit the production runtime autonomously
- silently change cognition
- activate code without review
- grant itself permissions
- bypass governance
- merge or deploy its own work

## Stable Runtime, Extensible Ecosystem

The frozen RC2 pipeline should become the stable answer-this-turn substrate.
Specialized future capabilities should attach above or beside it.

```text
Stable RC2 Cognitive Runtime
        |
        v
RC3 Goal / Plan / Monitor Layer
        |
        v
Plugin and Sandbox Interfaces
        |
        v
Specialized Functional Modules
```

Potential plugin families include:

- coding
- legal analysis
- finance
- biology
- engineering
- diagnostics
- mathematics
- simulation
- document processing
- external tool adapters

Plugins should remain independent from the cognitive core. The runtime should
know what a plugin does, what permissions it requires, how it is tested, and
how it is rolled back, without depending on the plugin's internal
implementation.

## Plugin Metadata Contract

Every future plugin should eventually declare:

- purpose
- capability
- required interfaces
- required permissions
- tools used
- network requirements
- filesystem access
- memory access
- safety constraints
- tests
- rollback procedure
- activation status
- Developer Overlay support

The core may route to a plugin under governance. The plugin must not become
hidden authority inside the substrate.

## Sandbox Engineering Workflow

Before a capability reaches the production runtime, it should pass through an
isolated engineering environment.

```text
Capability gap
        |
        v
Design
        |
        v
Experimental branch / sandbox
        |
        v
Compile and tests
        |
        v
Benchmark and safety review
        |
        v
Proposal package
        |
        v
External review
        |
        v
Operator decision
```

No automatic merge. No automatic deployment. No automatic activation.

The sandbox should be disposable. Production mutation must not occur inside it.

## Proposal Package

Every completed engineering proposal should include:

- objective
- architectural rationale
- files changed
- code diff summary
- validation performed
- benchmark impact
- safety review
- invariants checked
- risks
- limitations
- rollback plan
- confidence
- recommendation

The proposal should be understandable without reading the code.

## External Review Loop

DELTA should not be the final reviewer of its own work.

The intended review chain is:

```text
DELTA proposal
        |
        v
External review
        |
        v
Operator review
        |
        v
Merge or reject decision
```

External review should evaluate architecture, maintainability, reasoning
quality, regressions, safety, governance, unnecessary complexity, and benchmark
integrity.

## Controlled Forgetting

Controlled forgetting is a future governed capability, not an RC2 behavior.
It should be treated as substrate governance, not as erasure-by-default.

Distinct forgetting forms:

- working-memory expiration: ephemeral turn context naturally falls out of the
  bounded session window
- concept quarantine: suspect noncanonical concepts are hidden from default
  retrieval while preserved for audit
- concept deprecation: a reviewed concept remains inspectable but loses active
  retrieval authority
- edge deactivation: a graph edge is removed from active traversal while its
  provenance and rollback handle remain available
- curriculum exclusion: a concept, edge, or episode is marked ineligible for
  future training packets or distillation
- hard deletion: reserved for operator-approved cleanup of noncanonical data
  where audit and rollback requirements have been satisfied

Controlled forgetting must preserve:

- provenance
- reason for forgetting
- operator approval
- affected concepts or edges
- rollback or recovery procedure when applicable
- benchmark impact
- Developer Overlay visibility

It must not:

- silently hide inconvenient evidence
- rewrite history
- remove canonical knowledge without a separate canonical governance protocol
- mutate model weights
- create autonomous forgetting behavior

## Relationship To Distillation

Neural training remains a graduation event, not the mechanism of daily
learning.

The runtime may eventually produce reviewed curricula from successful and
failed cognitive episodes, analogy mappings, contradiction resolutions,
multi-concept synthesis, uncertainty cases, and corrected outputs. A training
packet should be created only after competency gates show the curriculum is
stable enough to graduate.

The runtime continues to provide governed memory, graph reasoning, rollback,
and operator review after any future checkpoint is distilled.

## RC3 Placement

RC3 should begin only after RC2 is frozen. RC3 may explore:

- goal-directed cognition
- planning
- introspection
- self-evaluation
- meta-reasoning
- controlled forgetting design
- operator-governed self-engineering
- plugin architecture
- sandbox experimentation

RC3 should not be used to finish RC2. It should build on RC2 as a stable
cognitive runtime.

## Recommendation

Complete the final validation pass, publish RC2 freeze documentation, create a
freeze tag only when the operator explicitly approves, then begin RC3 design
from this direction.

The long-term objective is not autonomous evolution. The objective is a
governed engineering collaborator whose proposals are evidence-backed,
isolated, externally reviewable, operator-approved, and reversible.

The initial RC3 pilot and freeze protocol is recorded in
`docs/RC3_OPERATOR_PILOT_AND_FREEZE_PROTOCOL.md`. That protocol keeps RC3 on
the governed path:

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

It explicitly rejects:

```text
Goal
-> Self-authorized action
-> Production mutation
```
