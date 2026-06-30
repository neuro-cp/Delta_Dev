# DELTA Roadmap

## Current Phase

Phase 2: Build The Cognitive Core

Cold-start note: read `docs/ARCHITECTURE.md`, then `docs/ROADMAP.md`, then
`docs/UPDATE.md` before continuing implementation.

The current goal is to make Delta understandable and runnable before adding
major new cognitive capabilities. Delta should now develop around a continuous
cognitive cycle rather than disconnected components.

## Core Cognitive Cycle

Delta's target loop is:

```text
Observe
Attend
Interpret
Reason
Plan
Act
Evaluate
Learn
Consolidate
Reflect
Goal Update
Observe
```

Memory is the substrate. The loop is the organism.

## Completed Milestones

- Added a root project README describing Delta as a cognitive substrate.
- Moved backup guidance into `docs/legacy_backup_inventory.md`.
- Added a focused smoke-test spine in `pyproject.toml`.
- Added a developer CLI at `tools/delta_cli.py`.
- Made runtime-backed recall optional for fast orchestration runs.
- Made replay enqueue prompting optional for non-interactive development runs.
- Added an append-only persistent memory store and CLI memory operations.
- Added the first explicit `CognitiveCycle` implementation.
- Added `docs/ARCHITECTURE.md` as the stable architectural constitution.
- Added relationship records and append-only relationship storage.
- Added an application-level attention service.
- Added a structured reflection engine.
- Attached relationship, attention, and reflection to the cognitive cycle.
- Forwarded attended memory context into orchestration as advisory metadata.
- Added the first non-authoritative Learning Region.
- Attached learning to the cognitive cycle after reflection.
- Added append-only learning record storage and CLI inspection.
- Added the first Knowledge Layer:
  - semantic knowledge records
  - explicit consolidation from learning records
  - contradiction records
  - prediction records
  - CLI knowledge inspection
- Added per-cycle working memory context and forwarded it into orchestration as
  advisory active context.
- Added a derived Self Model Region with temporal continuity, cognitive
  metrics, subsystem health, and cognitive health reporting.
- Added a first non-executing Simulation Region for comparing hypothetical
  futures.
- Added the first Agency slice:
  - persistent goal records
  - executive goal prioritization
  - proposed non-executing plans
  - explicit decision records
  - agency proposals
- Added `docs/COGNITIVE_GAP_ANALYSIS.md`.
- Added Phase 8 grounding/runtime foundations:
  - curated bootstrap knowledge
  - idempotent bootstrap loader
  - bounded runtime ticks
  - first Delta Console inspection surface
  - first runtime and postmortem reports
- Added initial consolidation governance and prediction validation.

## Phase 1: Stabilize Architecture

- Maintain a clear runnable orchestration path.
- Identify canonical systems versus legacy or experimental systems.
- Reduce side effects in developer entrypoints.
- Document current architecture decisions as they are made.
- Avoid broad rewrites until source-of-truth systems are identified.

## Phase 2: Strengthen Cognitive Substrate

- Make memory the center of the system.
- Treat raw memory as substrate, not as the whole organism.
- Maintain separate memory layers:
  - experience: immutable observations and actions
  - semantic: consolidated knowledge
  - episodic: sequences and timelines
  - working: active temporary context
- Define canonical persistent memory APIs.
- Define knowledge representation and relationship primitives.
- Strengthen contextual recall, indexing, confidence tracking, and consolidation.

## Phase 3: Develop Attention Architecture

- Define application-level attention interfaces.
- Support active context, memory relevance, goal relevance, novelty, conflict,
  and salience weighting.
- Keep attention modular and separate from model-internal transformer attention.

## Phase 4: Develop Regional Cognitive Architecture

- Establish clear subsystem boundaries for memory, attention, reasoning,
  planning, goals, perception, learning, and execution.
- Standardize interfaces between subsystems.
- Reduce tight coupling between runtime, learning, and execution surfaces.

## Phase 5: Production Readiness

- Establish stable package layout.
- Separate source, experiments, generated artifacts, and archives.
- Add repeatable setup and run commands.
- Harden tests around canonical APIs and user-facing entrypoints.

## Phase 6: Internal Simulation

- Keep simulation non-executing and cycle-compatible.
- Feed working memory, semantic knowledge, relationships, predictions, and
  goals into simulation.
- Produce hypothetical outcomes with confidence, risk, rationale, and evidence
  references.
- Feed simulation reports into planning only after planning has explicit
  interfaces.
- Compare later observations against simulated expectations for prediction
  validation.

## Phase 7: Agency And Adaptive Cognition

- Keep agency non-executing and fully inspectable.
- Complete goal evolution from learning and reflection outputs.
- Connect goals into attention, working memory, and simulation.
- Persist plans across sessions and attach execution outcomes later.
- Use decision records to explain why a goal, plan, or action was proposed.
- Begin adaptive prioritization from repeated success, repeated failure,
  uncertainty, and contradiction pressure.

## Phase 8: Grounding And First Runtime

- Seed foundational semantic concepts with provenance.
- Run bounded runtime ticks, not a permanent daemon.
- Keep interfaces as clients of the substrate, not the substrate itself.
- Observe runtime behavior through reports and the Delta Console.
- Stabilize knowledge evolution before longer runtimes.
- Prevent repeated runtime ticks from flooding semantic knowledge, predictions,
  or contradictions.

## Next Recommended Task

Continue governance and validation:

1. Replace token-overlap prediction validation with evidence-aware validation.
2. Add provenance-preserving confidence revision records for semantic knowledge.
3. Add goal progress feedback from runtime outcomes.
4. Add relationship strengthening between repeated runtime observations.
5. Design Global Workspace as a tick-local integration surface before deeper
   runtime coupling.
