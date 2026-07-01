# DELTA Roadmap

## Current Phase

Phase 12: Autonomous Cognitive Development And Experience Acquisition

Cold-start note: read `docs/ARCHITECTURE.md`, then `docs/ROADMAP.md`, then
`docs/INVARIANTS.md`, then `docs/UPDATE.md` before continuing implementation.

The current goal is to prove that Delta's existing cognitive substrate remains
stable, auditable, and bounded over longer runtimes. The roadmap should now ask:
what evidence says Delta is ready to build the next thing?
Phase 12 now focuses on improving cognition quality through directed
experience, curriculum, capability planning, provider learning, and governed
knowledge formation rather than adding new top-level cognitive regions.

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
- Replaced shallow token-overlap prediction validation with first-pass
  evidence-aware claim scoring that can append supported or failed prediction
  revisions.
- Added evidence-derived confidence policy and append-only semantic knowledge
  revisions carrying justification metadata.
- Added append-only contradiction resolution records that preserve both claims
  while recording resolution evidence and rationale.
- Added relationship weighting and append-only strengthening revisions for
  repeated relationship evidence.
- Added prediction quality metrics for latest prediction accuracy, evaluated
  coverage, failure rate, and average evidence score.
- Added reflection quality scoring with explainable dimensions for cycle
  inspection.
- Expanded Delta Console to expose prediction quality, contradiction state,
  weighted relationships, and reflection quality alongside existing runtime
  stores.
- Completed an isolated 1000-tick bounded runtime experiment with stable
  completion and controlled semantic/prediction growth.
- Added governance stress tests for duplicate consolidation, relationship
  weight caps, prediction latest-state metrics, and contradiction-pressure
  self-observation.
- Profiled runtime performance and added cached simulation tokenization,
  improving a 200-tick isolated run from `10.63` to `15.43` ticks/second.
- Added a canonical model abstraction layer and dynamic GGUF discovery from
  `G:\models`, preserving compatibility aliases for local models.
- Added explicit model routing policy and append-only model observatory records
  for inference latency, token counts, confidence, and model usage.
- Added an isolated cognitive evaluation harness for repeatable cycle-level
  evaluation cases.
- Added multi-model comparison over canonical inference results, including
  agreement, confidence spread, latency spread, and evidence counts.
- Added model inventory, inference observatory metrics, and recent inference
  events to the read-only Delta Console.
- Clarified that local models, GPT, and future tools are interchangeable
  reasoning providers. Delta's long-term routing objective is capability
  selection under governance, not a model leaderboard.
- Added a Curriculum Engine that generates directed cognitive experience tasks
  by domain, adapts difficulty from observed evaluation performance, and marks
  generated tasks as experiences rather than knowledge.
- Added an Experience Generator and append-only Experience Store for provider
  generated observations, hypotheses, plans, simulations, predictions, and
  reflections that remain pending governance and cannot directly create
  semantic knowledge.
- Added a Capability Planner so intent is mapped to required cognitive
  capabilities before provider allocation, and routing can consume capability
  plans without replacing them.
- Added dynamic provider learning from inference observatory records, deriving
  provider and capability profiles from observed latency, confidence, and
  evidence count without hardcoded permanent preferences.
- Added read-only knowledge quality reports that summarize evidence,
  counter-evidence, relationships, prediction outcomes, revisions, validation,
  derived confidence, and uncertainty.
- Added first world-model records for objects, events, and relations extracted
  from governed experiences only, with append-only world-model snapshots.
- Expanded the runtime experiment laboratory with structured experiment kinds,
  curriculum prompts, large tick target reporting, and curriculum coverage
  summaries while preserving isolated stores.
- Expanded the Delta Console cognitive observatory with generated experiences,
  provider effectiveness, knowledge quality, and world-model snapshots.
- Added read-only knowledge distillation reports for stable concepts, weak
  concepts, and discard candidates.
- Added Codex mentorship reports that inspect runtime, knowledge quality, and
  provider evidence to propose engineering tasks without editing Delta's
  cognition.
- Added a cognitive benchmark comparator and CLI that separate engineering
  correctness, cognitive correctness, and task performance when comparing
  baseline and candidate runtime summaries.
- Ran Phase 13 experience-scaling curriculum experiments at 100, 250, 500, and
  1000 ticks in isolated stores. Results showed runtime stability but flat
  cognitive metrics and declining throughput.
- Added novelty and experience-utility measurement. The 1000-tick curriculum
  run showed low average novelty (`0.1144`), low average information gain
  (`0.1279`), low average utility (`0.1371`), and zero average surprise,
  supporting the hypothesis that experience quality is the current bottleneck.
- Added provider experience-utility profiling so local providers can be
  compared by capability-local experience utility rather than global rank.

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

## Phase 8: Governance And Stability

Goals:

- Stable bounded runtime.
- Controlled semantic growth.
- Correct current-state metrics over append-only history.
- Prediction lifecycle tracking.
- Justification-derived confidence from evidence, validation history,
  contradictions, and provenance.
- Duplicate suppression.
- Provenance validation.

Exit criteria:

- 100-tick isolated runtime without runaway growth.
- Stable self-model metrics based on latest valid state.
- No duplicate semantic explosion.
- Predictions remain bounded and traceable through revisions.
- Confidence values are explainable derived summaries of evidence-backed
  justification, not unexplained mutable state.
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

- Canonical reasoning provider abstraction layer.
- Capability selection before provider selection.
- Local GGUF model integration.
- GPT integration as an optional provider.
- Speech.
- Vision.
- External tools.

Exit criteria:

- External and local models improve reasoning without compromising governance.
- Provider routing is based on needed capability, observed reliability, latency,
  cost, context size, and task fit.

## Phase 12: Autonomous Cognitive Development

Goals:

- Directed curriculum rather than random inference.
- Experience generation that produces observations, hypotheses, plans,
  simulations, predictions, and reflections without directly creating
  knowledge.
- Capability planning before provider allocation.
- Dynamic provider learning from inference observatory records.
- Richer knowledge quality signals.
- World model construction from accumulated governed experience.
- Long-runtime laboratory with isolated stores and comprehensive reports.
- Cognitive observatory console expansion.
- Knowledge distillation from stable, highly supported runtime findings.
- Codex mentorship workflow based on reports and observed deficiencies.
- Hardware-aware provider manager that keeps only one local GGUF provider
  resident at a time and unloads between provider switches.
- Provider Qualification Suite that probes discovered GGUFs before experiment
  scheduling and records load, inference, memory, VRAM, and capability status.
- Unattended experiment scheduler for capability-specific queues, generated
  experience scoring, and provider utility accumulation.

Exit criteria:

- Delta can run structured cognitive development experiments without mutating
  production stores.
- Generated experience enters governance before knowledge formation.
- Provider allocation improves from observed evidence rather than hardcoded
  permanent preference.
- Runtime reports explain cognitive quality, not only mechanical success.
- Benchmarks can compare shorter and longer experience runs and report
  insufficient data honestly when a capability question cannot yet be answered.
- Local provider experiments can run serially on constrained VRAM without
  moving Delta's persistent state into the provider.
- Provider experiments are gated by an empirical provider capability database
  when one exists.
- The first integrated provider smoke run completes across the qualified local
  provider pool and reports capability-level experience utility.

## Maturity Scorecard

These percentages are explicit engineering estimates, not objective truth. They
should change only when runtime evidence or implementation review justifies it.

| Capability | Status | Confidence |
| --- | --- | --- |
| Experience Memory | Stable | 95% |
| Relationships | Stable | 90% |
| Semantic Knowledge | Stable | 80% |
| Consolidation | Stable | 75% |
| Prediction | Experimental | 60% |
| Justification-Derived Confidence | Experimental | 55% |
| Self Model | Stable | 80% |
| Simulation | Experimental | 65% |
| Agency | Experimental | 55% |
| Runtime | Stable | 85% |
| Console | Early inspection surface | 40% |

## Stabilization Rule

For the next several milestones, assume Delta has enough cognitive regions.
Unless a fundamental architectural deficiency is discovered, do not solve
problems by creating additional top-level regions. Prefer improving governance,
interaction quality, observability, scalability, and long-run stability of the
existing architecture.

## Next Recommended Task

Continue governance and validation:

1. Do not attempt 10,000 ticks until average experience utility improves beyond
   the Phase 13 baseline.
2. Use `reports/phase14_calibration_report.md` as the current cognitive
   calibration baseline.
3. Generate a larger non-repeating governed objective set before longer runs.
4. Add explicit outcome observations for open predictions before 250+ cycles.
5. Profile providers by capability-local experience utility rather than global
   rank.
6. Replace repeated difficulty-1 curriculum templates with utility-seeking
   curriculum generation.
7. Add held-out task-performance suites for coding, research, scheduling, and
   planning.
8. Reduce repeated JSONL full-store reads in runtime hot paths.
9. Deepen evidence-aware prediction validation beyond first-pass claim scoring.
10. Add goal progress feedback from runtime outcomes.
11. Design Global Workspace as a tick-local integration surface before deeper
   runtime coupling.
