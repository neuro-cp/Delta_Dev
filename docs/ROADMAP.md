# DELTA Roadmap

## Current Phase

Phase 8: Governance And Stability

Cold-start note: read `docs/ARCHITECTURE.md`, then `docs/ROADMAP.md`, then
`docs/INVARIANTS.md`, then `docs/UPDATE.md` before continuing implementation.

The current goal is to prove that Delta's existing cognitive substrate remains
stable, auditable, and bounded over longer runtimes. The roadmap should now ask:
what evidence says Delta is ready to build the next thing?

2026-10-19 evidence: isolated 10/25/50/100-tick mock runs pass bookkeeping checks;
86 configured tests pass, one is skipped. Read `docs/TRUST_REPORT.md` and
`docs/STABILITY_REPORT.md`. These results do not complete the governance phase:
external evidence, confidence revision, historical-state repair and recovery
remain unresolved.

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

## Grounding And First Runtime Foundations

- Seed foundational semantic concepts with provenance.
- Run bounded runtime ticks, not a permanent daemon.
- Keep interfaces as clients of the substrate, not the substrate itself.
- Observe runtime behavior through reports and the Delta Console.
- Stabilize knowledge evolution before longer runtimes.
- Prevent repeated runtime ticks from flooding semantic knowledge, predictions,
  or contradictions.

## Phase 8: Governance And Stability

Goals:

- Stable bounded runtime.
- Controlled semantic growth.
- Correct current-state metrics over append-only history.
- Prediction lifecycle tracking.
- Evidence-based confidence evolution.
- Duplicate suppression.
- Provenance validation.

Exit criteria:

- 100-tick isolated runtime without runaway growth.
- Stable self-model metrics based on latest valid state.
- No duplicate semantic explosion.
- Predictions remain bounded and traceable through revisions.
- Confidence is unchanged without new evidence, decreases when contrary evidence
  warrants it, and does not change again when the same evidence is replayed.
- Agency proposals remain bounded and non-executing.

## Phase 9: Observability

Goals:

- Delta Console.
- Live cognitive timeline.
- Region activity visualization.
- Working memory inspector.
- Attention inspector.
- Knowledge graph viewer.
- Runtime debugger.

Exit criteria:

- A developer can explain why Delta made every important cognitive decision.

## Phase 10: Grounded Intelligence

Goals:

- Richer bootstrap knowledge.
- Semantic organization.
- Curiosity and question formation.
- Knowledge revision.
- Long-term learning.

Exit criteria:

- Delta demonstrates measurable improvement after repeated runtime experiments.

## Phase 11: External Cognition

Goals:

- GPT integration.
- Local model integration.
- Speech.
- Vision.
- External tools.

Exit criteria:

- External models improve reasoning without compromising governance.

## Maturity Scorecard

The previous subjective percentages have been replaced with observed evidence.

| Capability | Status | Evidence / Limitation |
| --- | --- | --- |
| Experience Memory | Bounded-run validated | 216 records after 100 ticks; crash recovery untested |
| Relationships | Limited | One temporal link per successful cycle; no causal learning |
| Semantic Knowledge | Governance repaired | Preserves distinct claims and provenance; review incomplete |
| Consolidation | Explicit claims only | No internal fact growth; no automatic factual extraction |
| Prediction | Explicit assessments | Lifecycle tested; no automatic domain evaluator |
| Confidence Evolution | Not implemented | Original forecast retained; semantic calibration absent |
| Self Model | Partially validated | Current counts repaired; several health metrics remain proxies |
| Simulation | Heuristic | Weighted lexical evidence; not a learned world simulator |
| Agency | Proposal only | Bounded in all runs; no execution/goal progress feedback |
| Runtime | 100 mock ticks validated | No proof of multi-day, multiwriter or real-model stability |
| Console | Basic inspector exists | Recorded agency/current predictions; richer inspection pending |

## Stabilization Rule

For the next several milestones, assume Delta has enough cognitive regions.
Unless a fundamental architectural deficiency is discovered, do not solve
problems by creating additional top-level regions. Prefer improving governance,
interaction quality, observability, scalability, and long-run stability of the
existing architecture.

## Next Recommended Task

Continue governance and validation:

1. Add one governed external-evidence ingestion/review episode with a falsifiable
   prediction and independent outcome fixture.
2. Audit old self-validated predictions and implicit semantic supersessions
   without rewriting history.
3. Add justified confidence revision and goal-progress feedback from outcomes.
4. Establish crash recovery and single-writer ownership before longer runs.
5. Measure real region activity before deciding whether a Global Workspace adds
   value; no new top-level region is currently justified by this evaluation.
