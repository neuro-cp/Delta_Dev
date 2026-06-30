# DELTA Update Log

This is the canonical running handoff log for Delta development. A new Codex
session should read `docs/ARCHITECTURE.md`, then `docs/ROADMAP.md`, then this
file before making changes.

## 2026-06-30

### Summary

Completed a small Phase 1 milestone focused on making Delta easier to run and
resume. The main functional addition is a developer CLI that can exercise the
orchestration loop without requiring local GGUF models or runtime-backed recall.
This update also adds the first explicit persistent memory vertical slice.
It now adds the first explicit cognitive cycle wrapper.
It now adds the first relationship, attention, and reflection services attached
to that cycle.
It now forwards attended memory context into orchestration as advisory metadata.
It now adds the first non-authoritative Learning Region attached to the cycle.
It now adds the first Knowledge Layer: explicit semantic consolidation,
contradiction records, and prediction records.
It now adds canonical per-cycle Working Memory and forwards it into
orchestration/model prompts as advisory active context.
It now adds a derived Self Model Region with temporal continuity, cognitive
metrics, subsystem health, and cognitive health reporting.
It now adds the first non-executing Simulation Region for comparing
hypothetical futures.
It now adds the first Agency slice: persistent goals, executive prioritization,
non-executing plans, explicit decisions, and agency proposals.
It now adds Phase 8 grounding and runtime foundations: curated bootstrap
knowledge, a bounded runtime tick loop, first console foundations, first-life
runtime reporting, historical concept review, and first consolidation
governance after observing runaway amplification.
It now adds `docs/INVARIANTS.md` and shifts the roadmap toward
evidence-gated governance, stability, observability, and maturity scoring before
additional capability expansion.

### Architectural Decisions

- Runtime-backed recall construction is now optional via `enable_recall`.
- Replay enqueue prompting is now optional via `enable_replay_prompt`.
- The CLI defaults to fast local development behavior:
  - mock model router enabled
  - runtime recall disabled
  - replay prompting disabled
- Real model routing remains available through `--model real`.
- Runtime recall remains available through `--recall`.
- Persistent memory is append-only JSONL by default at
  `data/memory/persistent_memory.jsonl`.
- Persistent memory is explicit: records are added through CLI flags and do not
  mutate runtime behavior automatically.
- Persistent recall indexes record text, tags, and metadata. This is necessary
  because some outputs are too terse to recall without their originating prompt.
- Delta now has an explicit cycle path:
  observe -> interpret/reason -> store experience -> reflect.
- Relationship formation, consolidation, goals, attention, and richer action are
  represented as pending cycle stages rather than silently omitted.
- Relationship formation now records a direct temporal sequence relationship
  between cycle observation and cycle output.
- Attention now ranks recalled memories before interpretation/reasoning.
- Attended memories are forwarded into orchestration as advisory metadata.
- Model routes include attended context in the prompt payload with an explicit
  warning that it is advisory memory, not guaranteed truth.
- Reflection now emits structured learned/repeated/surprise/conflict and
  consolidation-candidate data.
- Learning now receives prompt, output, attended context, and reflection output.
- Learning emits durable non-authoritative records containing semantic
  candidates, confidence-update suggestions, questions, goal candidates, and
  consolidation candidates.
- Learning records are stored separately from memory records.
- Semantic knowledge records are stored separately from autobiographical memory.
- Consolidation promotes learning semantic candidates into semantic knowledge
  without deleting experience or learning records.
- Contradiction records preserve conflicting claims instead of overwriting them.
- Prediction records are generated from sufficiently confident semantic
  knowledge.
- Working Memory is assembled per cycle from observation, attended experience,
  semantic knowledge, and open predictions.
- Reflection inspects working memory before it disappears.
- The Self Model is derived and non-authoritative. It computes from existing
  regions and must not become a duplicate source of truth.
- Self-observations are structured report outputs, not semantic knowledge.
- Simulation is non-executing. It can estimate hypothetical outcomes,
  confidence, risk, and supporting evidence, but it cannot choose actions or
  mutate state.
- Agency owns no knowledge and has no execution authority.
- Goals and plans are persistent append-only records. Agency proposals and
  decisions are inspectable recommendations only.
- Executive control prioritizes cognitive work. It does not replace attention,
  planning, simulation, or execution.
- Delta may expose conversation, coding, automation, robotics, dashboards,
  APIs, or future embodied inputs. These are clients of the substrate, not the
  substrate itself. The architecture must not optimize around one interface.
- Delta's near-term roadmap is evidence-gated. The question is no longer only
  what should be built next, but what evidence shows Delta is ready for it.
- For the next milestones, Delta should prefer governance, observability,
  reproducibility, metric accuracy, and long-run stability over adding new
  top-level cognitive regions.
- Bootstrap knowledge is curated and idempotent. It seeds only foundational
  primitives with explicit provenance.
- Runtime execution is bounded by ticks or operator interruption. Delta does not
  run as a permanent daemon by default.
- Consolidation now suppresses near-duplicate semantic promotions.
- Prediction generation now suppresses near-duplicate expectations.
- Prediction validation is append-only and currently shallow. It can mark
  predictions as supported from token-overlap observations, but this is not deep
  semantic validation.
- `docs/UPDATE.md` is the canonical handoff log. `docs/ROADMAP.md` is the
  canonical planning file. `docs/ARCHITECTURE.md` is the canonical architecture
  constitution.

### Files Modified

- `orchestration/loop/cognitive_loop.py`
- `tools/delta_cli.py`
- `memory/persistent/__init__.py`
- `memory/persistent/memory_record.py`
- `memory/persistent/memory_store.py`
- `memory/relationships/__init__.py`
- `memory/relationships/relationship_record.py`
- `memory/relationships/relationship_store.py`
- `orchestration/attention/__init__.py`
- `orchestration/attention/attention_item.py`
- `orchestration/attention/attention_service.py`
- `orchestration/cycle/__init__.py`
- `orchestration/cycle/cognitive_cycle.py`
- `orchestration/cycle/cycle_result.py`
- `orchestration/reflection/__init__.py`
- `orchestration/reflection/reflection_engine.py`
- `orchestration/reflection/reflection_record.py`
- `learning/region/__init__.py`
- `learning/region/learning_engine.py`
- `learning/region/learning_record.py`
- `learning/region/learning_store.py`
- `knowledge/__init__.py`
- `knowledge/consolidation_engine.py`
- `knowledge/contradiction_engine.py`
- `knowledge/contradiction_record.py`
- `knowledge/prediction_engine.py`
- `knowledge/prediction_record.py`
- `knowledge/semantic_record.py`
- `knowledge/semantic_store.py`
- `memory/working_memory/active_context.py`
- `orchestration/self_model/__init__.py`
- `orchestration/self_model/self_model.py`
- `knowledge/bootstrap.py`
- `orchestration/runtime/__init__.py`
- `orchestration/runtime/cognitive_runtime.py`
- `orchestration/tests/runtime/__init__.py`
- `orchestration/tests/runtime/test_bootstrap_runtime.py`
- `tools/delta_console.py`
- `tools/runtime_report.py`
- `docs/BOOTSTRAP_KNOWLEDGE.md`
- `docs/FIRST_RUNTIME_REPORT.md`
- `docs/FIRST_LIFE_POSTMORTEM.md`
- `docs/HISTORICAL_CONCEPT_REVIEW.md`
- `docs/GOVERNANCE_RUNTIME_REPORT.md`
- `docs/INVARIANTS.md`
- `docs/COGNITIVE_GAP_ANALYSIS.md`
- `orchestration/simulation/__init__.py`
- `orchestration/simulation/simulation_region.py`
- `orchestration/tests/self_model/test_self_model.py`
- `orchestration/tests/simulation/test_simulation_region.py`
- `orchestration/agency/__init__.py`
- `orchestration/agency/agency_region.py`
- `orchestration/agency/decision_engine.py`
- `orchestration/agency/executive_controller.py`
- `orchestration/agency/goal_system.py`
- `orchestration/agency/planning_engine.py`
- `orchestration/tests/agency/test_agency_region.py`
- `integration/model_runtime/prompt_builder.py`
- `docs/COGNITIVE_GAP_ANALYSIS.md`
- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/UPDATE.md`

Earlier uncommitted work in this workspace also includes:

- `README.md`
- `docs/development_roadmap.md`
- `docs/legacy_backup_inventory.md`
- `pyproject.toml`
- `.gitignore`
- `orchestration/execution/resolution_executor.py`
- `orchestration/tests/execution/test_resolution_executor.py`
- `integration/tests/substrate_surface/test_mode_behavior_policy.py`
- real-model test skip behavior in orchestration tests

### Rationale

Rapid development needs a reliable vertical slice. The CLI provides a direct
way to exercise Delta's current task typing, routing, execution, evaluation,
and mock model-plugin boundary without paying runtime compilation cost on every
run.

The persistent memory slice gives Delta a durable place to accumulate operator
notes and selected orchestration outputs. It is intentionally not wired into
decision authority yet.

The cognitive cycle reframes development around process continuity. Memory is
the substrate; the repeated observe/interpret/store/reflect loop is the first
organism-level behavior.

The relationship, attention, and reflection additions move the cycle from a
request-response wrapper toward a minimal cognitive process. The implementations
are intentionally simple but cycle-attached.

Forwarding attended context closes the first loop between memory, attention,
and interpretation. Attention still does not control execution; it supplies
structured advisory context.

The Learning Region turns reflection into persistent adaptation pressure. It
does not train models and does not apply changes directly. It records what Delta
might learn next.

The Knowledge Layer turns selected learning records into durable semantic
knowledge while preserving provenance. It is explicit, non-destructive, and
separate from autobiographical memory.

Working Memory now provides the cycle's temporary active context. It bridges
attention, knowledge, prediction, interpretation, and reflection without
becoming durable truth.

The Self Model gives Delta introspection without adding authority. It derives
metrics, temporal continuity, subsystem health, cognitive health, and
self-observations from existing stores.

The Simulation Region gives Delta the first mechanism for evaluating possible
futures before planning exists. It is intentionally read-only and
non-executing.

The Agency slice starts turning internal state into proposed intentional
behavior. It adds durable goals, proposed plans, decision scoring, and executive
prioritization while preserving the boundary that nothing executes
automatically.

The Phase 8 runtime slice grounds Delta with a small curated concept set and
tests whether the cognitive cycle can run continuously without pretending to be
intelligent. The first-life run stayed stable but exposed a real architectural
problem: consolidation and prediction amplified faster than validation,
confidence revision, and goal feedback could correct them. The follow-up
governance pass suppresses duplicate semantic promotion and duplicate
prediction generation, then validates a short five-tick run with controlled
semantic growth.

### Validation

Run:

```powershell
.\.venv311\Scripts\python.exe tools\delta_cli.py "What is 2 + 5?" --model none
.\.venv311\Scripts\python.exe tools\delta_cli.py "Compare replay memory and working memory" --model mock
.\.venv311\Scripts\python.exe tools\delta_cli.py --remember "Delta is a persistent cognitive substrate."
.\.venv311\Scripts\python.exe tools\delta_cli.py --recall-memory "persistent substrate"
.\.venv311\Scripts\python.exe tools\delta_cli.py "What is 4 + 6?" --model none --cycle
.\.venv311\Scripts\python.exe tools\delta_cli.py "What is 8 + 2?" --model none --cycle --json
.\.venv311\Scripts\python.exe tools\delta_cli.py "Compare Delta memory and attention" --model mock --cycle --json
.\.venv311\Scripts\python.exe tools\delta_cli.py "Compare Delta learning and reflection" --model mock --cycle --json
.\.venv311\Scripts\python.exe tools\delta_cli.py --list-learning
.\.venv311\Scripts\python.exe tools\delta_cli.py --consolidate-knowledge
.\.venv311\Scripts\python.exe tools\delta_cli.py --list-knowledge
.\.venv311\Scripts\python.exe tools\delta_cli.py --list-predictions
.\.venv311\Scripts\python.exe tools\delta_cli.py "Compare Delta working memory and attention" --model mock --cycle --json
.\.venv311\Scripts\python.exe tools\delta_cli.py --self-model --json
.\.venv311\Scripts\python.exe tools\delta_cli.py --simulate-option "run knowledge consolidation" --simulate-option "skip knowledge consolidation" --json
.\.venv311\Scripts\python.exe tools\delta_cli.py --goal-path .tmp\agency_goals.jsonl --create-goal "Improve prediction accuracy"
.\.venv311\Scripts\python.exe tools\delta_cli.py --goal-path .tmp\agency_goals.jsonl --list-goals
.\.venv311\Scripts\python.exe tools\delta_cli.py --goal-path .tmp\agency_goals.jsonl --plan-path .tmp\agency_plans.jsonl --plan-goals --json
.\.venv311\Scripts\python.exe tools\delta_cli.py --goal-path .tmp\agency_goals.jsonl --agency-report --json
.\.venv311\Scripts\python.exe tools\delta_cli.py --bootstrap-knowledge
.\.venv311\Scripts\python.exe tools\delta_cli.py --runtime-ticks 5 --runtime-interval 1 --model mock
.\.venv311\Scripts\python.exe tools\delta_cli.py --write-runtime-report
.\.venv311\Scripts\python.exe tools\delta_console.py --port 8765
.\.venv311\Scripts\python.exe -m pytest orchestration\tests\loop\test_cognitive_loop.py orchestration\tests\execution\test_resolution_executor.py
```

Expected status:

- deterministic solver path succeeds
- mock model path succeeds
- explicit memory storage and recall succeed
- cognitive cycle stores observation and output memories
- cognitive cycle stores a temporal relationship between observation and output
- cognitive cycle ranks recalled memories through attention
- cognitive cycle forwards attended context into orchestration metadata
- cognitive cycle emits structured reflection metadata
- cognitive cycle emits and stores structured learning records
- knowledge consolidation creates semantic records from learning candidates
- confident semantic records generate open predictions
- working memory stage assembles active context
- reflection receives working memory summary
- self-model report derives metrics and health from existing stores
- simulation report compares hypothetical futures without executing them
- goal creation and goal listing work through explicit CLI commands
- planning creates proposed non-executing plans
- agency report proposes a next action without execution authority
- bootstrap seeding is idempotent
- bounded runtime executes the requested number of ticks
- runtime events are written for inspection
- console state endpoint renders current cognitive stores
- duplicate semantic consolidation is suppressed
- duplicate prediction generation is suppressed
- shallow prediction validation can append supported prediction revisions
- targeted orchestration tests pass

Latest observed cycle validation:

- command: `.\.venv311\Scripts\python.exe tools\delta_cli.py "What is 4 + 6?" --model none --cycle`
- route: `deterministic_solver`
- output: `10`
- persisted memories: one observation record and one output record

Latest relationship/attention/reflection validation:

- command: `.\.venv311\Scripts\python.exe tools\delta_cli.py "What is 8 + 2?" --model none --cycle --json`
- route: `deterministic_solver`
- output: `10`
- persisted memories: observation and output records
- persisted relationship: one `temporal_sequence` record
- attention stage: ranked recalled memories with factor scores
- reflection stage: emitted learned, repeated, conflict, surprise, and
  consolidation-candidate fields

Latest attended-context validation:

- command: `.\.venv311\Scripts\python.exe tools\delta_cli.py "Compare Delta memory and attention" --model mock --cycle --json`
- route: `llm`
- attended context count: `2`
- prompt context: forwarded as advisory metadata to orchestration/model route

Latest learning validation:

- command: `.\.venv311\Scripts\python.exe tools\delta_cli.py "Compare Delta learning and reflection" --model mock --cycle --json`
- route: `llm`
- learning stage: emitted one learning record
- semantic candidates: `1`
- confidence updates: `4`
- command: `.\.venv311\Scripts\python.exe tools\delta_cli.py --list-learning`
- result: stored learning record is inspectable

Latest knowledge validation:

- command: `.\.venv311\Scripts\python.exe tools\delta_cli.py --consolidate-knowledge --knowledge-path .tmp\knowledge.jsonl --contradiction-path .tmp\contradictions.jsonl --prediction-path .tmp\predictions.jsonl`
- semantic records created: `2`
- contradictions detected: `0`
- predictions generated: `2`

Latest working-memory validation:

- command: `.\.venv311\Scripts\python.exe tools\delta_cli.py "Compare Delta working memory and attention" --model mock --cycle --json`
- working memory items: `6`
- working memory included: observation plus attended experience
- reflection metadata included working memory summary

Latest self-model validation:

- command: `.\.venv311\Scripts\python.exe tools\delta_cli.py --self-model --json`
- generated temporal continuity, subsystem health, cognitive health, confidence
  distribution, and self-observations
- observed warning: learning records exist but semantic knowledge is empty

Latest simulation validation:

- command: `.\.venv311\Scripts\python.exe tools\delta_cli.py --simulate-option "run knowledge consolidation" --simulate-option "skip knowledge consolidation" --json`
- generated two hypothetical outcomes
- report marked simulation as non-executing

Latest agency validation:

- command: `.\.venv311\Scripts\python.exe tools\delta_cli.py --goal-path .tmp\agency_goals.jsonl --create-goal "Improve prediction accuracy"`
- command: `.\.venv311\Scripts\python.exe tools\delta_cli.py --goal-path .tmp\agency_goals.jsonl --list-goals`
- command: `.\.venv311\Scripts\python.exe tools\delta_cli.py --goal-path .tmp\agency_goals.jsonl --plan-path .tmp\agency_plans.jsonl --plan-goals --json`
- command: `.\.venv311\Scripts\python.exe tools\delta_cli.py --goal-path .tmp\agency_goals.jsonl --agency-report --json`
- result: created a persistent temporary goal, produced a proposed plan, and
  generated an agency proposal with `execution_authority=false`

Latest first-life runtime:

- report: `docs/FIRST_RUNTIME_REPORT.md`
- ticks: `20`
- result: runtime remained stable, but consolidation/prediction/contradiction
  amplification was observed
- postmortem: `docs/FIRST_LIFE_POSTMORTEM.md`
- recommended correction: add consolidation governance, prediction validation,
  confidence revision, goal feedback, and Global Workspace design

Latest governance validation:

- report: `docs/GOVERNANCE_RUNTIME_REPORT.md`
- bootstrap result: `16` semantic concepts, `16` predictions, `4` goals
- runtime result: `5` requested ticks and `5` completed ticks
- semantic growth: `1` new semantic record on tick 1, `0` on ticks 2 through 5
- latest prediction state: `17` predictions, `0` open predictions after shallow
  validation
- warning: validation is token-overlap based and should not be treated as
  robust predictive cognition

Latest targeted tests:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_bootstrap_runtime.py orchestration\tests\agency\test_agency_region.py orchestration\tests\self_model\test_self_model.py orchestration\tests\simulation\test_simulation_region.py orchestration\tests\loop\test_cognitive_loop.py orchestration\tests\execution\test_resolution_executor.py`
- result: `16 passed`

Latest compile check:

- command: `.\.venv311\Scripts\python.exe -m py_compile knowledge\semantic_store.py knowledge\prediction_engine.py knowledge\consolidation_engine.py orchestration\runtime\cognitive_runtime.py tools\delta_cli.py`
- result: passed

### Cold-Session Resume Instructions

1. Read `docs/ARCHITECTURE.md`.
2. Read `docs/ROADMAP.md`.
3. Read `docs/UPDATE.md`.
4. Inspect current git status before editing:

```powershell
git status --short --branch
```

5. Validate the current functional slice:

```powershell
.\.venv311\Scripts\python.exe tools\delta_cli.py "What is 4 + 6?" --model none --cycle
.\.venv311\Scripts\python.exe tools\delta_cli.py --recall-memory "What is 4 + 6"
.\.venv311\Scripts\python.exe tools\delta_cli.py "What is 8 + 2?" --model none --cycle --json
.\.venv311\Scripts\python.exe tools\delta_cli.py "Compare Delta memory and attention" --model mock --cycle --json
.\.venv311\Scripts\python.exe tools\delta_cli.py "Compare Delta working memory and attention" --model mock --cycle --json
.\.venv311\Scripts\python.exe tools\delta_cli.py --self-model --json
.\.venv311\Scripts\python.exe tools\delta_cli.py --simulate-option "run knowledge consolidation" --simulate-option "skip knowledge consolidation" --json
.\.venv311\Scripts\python.exe tools\delta_cli.py --goal-path .tmp\agency_goals.jsonl --create-goal "Improve prediction accuracy"
.\.venv311\Scripts\python.exe tools\delta_cli.py --goal-path .tmp\agency_goals.jsonl --agency-report --json
.\.venv311\Scripts\python.exe tools\delta_cli.py --bootstrap-knowledge
.\.venv311\Scripts\python.exe tools\delta_cli.py --runtime-ticks 5 --runtime-interval 1 --model mock
.\.venv311\Scripts\python.exe tools\delta_cli.py --list-learning
.\.venv311\Scripts\python.exe tools\delta_cli.py --consolidate-knowledge
.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_bootstrap_runtime.py orchestration\tests\agency\test_agency_region.py orchestration\tests\self_model\test_self_model.py orchestration\tests\simulation\test_simulation_region.py orchestration\tests\loop\test_cognitive_loop.py orchestration\tests\execution\test_resolution_executor.py
```

6. Continue with the recommended next task unless the user redirects.

Current functional entrypoints:

- `tools/delta_cli.py --model none` for deterministic orchestration.
- `tools/delta_cli.py --model mock` for fast model-plugin simulation.
- `tools/delta_cli.py --model real` for local GGUF model routing.
- `tools/delta_cli.py --cycle` for one observe/interpret/store/reflect cycle.
- `tools/delta_cli.py --remember` for explicit persistent memory writes.
- `tools/delta_cli.py --recall-memory` for persistent memory recall.
- `tools/delta_cli.py --list-models` for model discovery.
- `tools/delta_cli.py --self-model` for derived self-model and cognitive
  health inspection.
- `tools/delta_cli.py --simulate-option` for non-executing hypothetical future
  comparison.
- `tools/delta_cli.py --create-goal` for explicit persistent goal creation.
- `tools/delta_cli.py --list-goals` for active goal inspection.
- `tools/delta_cli.py --plan-goals` for proposed non-executing plan creation.
- `tools/delta_cli.py --agency-report` for proposed next-action inspection.
- `tools/delta_cli.py --bootstrap-knowledge` for idempotent foundational
  semantic seeding.
- `tools/delta_cli.py --runtime-ticks N` for bounded cognitive runtime ticks.
- `tools/delta_cli.py --runtime-until-interrupted` for operator-bounded runtime
  operation.
- `tools/delta_cli.py --write-runtime-report` for first-runtime report
  generation.
- `tools/delta_console.py --port 8765` for the read-only cognitive observatory.

Important local paths:

- persistent memory data: `data/memory/persistent_memory.jsonl`
- relationship data: `data/memory/relationships.jsonl`
- learning data: `data/learning/learning_records.jsonl`
- semantic knowledge data: `data/knowledge/semantic_knowledge.jsonl`
- contradiction data: `data/knowledge/contradictions.jsonl`
- prediction data: `data/knowledge/predictions.jsonl`
- goal data: `data/agency/goals.jsonl`
- plan data: `data/agency/plans.jsonl`
- runtime event data: `data/runtime/events.jsonl`
- local models: `C:\Users\Admin\Desktop\models`
- external legacy backup: `C:\Users\Admin\Desktop\delta backup`

### Known Issues

- The broad historical test tree still contains collection failures from
  missing or renamed modules.
- Root-level scratch files and generated artifacts are still mixed with source.
- Persistent memory is not yet a canonical center of the system.
- Persistent memory exists, but it is currently a minimal append-only store with
  token-overlap recall only.
- The current memory schema is acceptable as a first ingestion layer, but it is
  not sufficient as Delta's final knowledge schema. It needs separate
  relationship, contradiction, consolidation, and provenance layers.
- The cycle implementation is deliberately incomplete. It records pending stages
  explicitly so future work has stable attachment points.
- Attention currently uses simple task-relevance/confidence/operator-priority
  scoring. It does not yet include goals, contradiction, novelty, or nervous
  system signals.
- Reflection currently produces basic structured fields. It does not yet update
  confidence, merge memories, or create semantic knowledge.
- Relationship storage currently records direct temporal sequence links only.
- Attended context is advisory only. It is passed into interpretation/model
  payloads and assembled into per-cycle working memory, but it has no execution
  authority.
- Working memory is per-cycle only. It is not yet connected to active goals.
- Self Model is generated on demand. It is not scheduled into a continuous
  runtime loop.
- Simulation exists as an explicit non-executing region, but it is not yet fed
  back into planning, prediction validation, or learning.
- Agency exists as a proposal layer only. It is not yet integrated into the
  main cognitive cycle.
- Goals can be created explicitly, but learning/reflection goal candidates are
  not yet promoted into persistent goals.
- Plans persist, but execution outcomes are not yet attached as episodic
  memories.
- Learning records are advisory only. They do not yet promote semantic memory,
  update confidence, or create goals.
- Knowledge consolidation exists, but confidence evolution is still proposal
  based. Semantic confidence is not yet revised from prediction success/failure.
- Prediction generation exists, but prediction evaluation against future
  observations is only shallow token-overlap validation.
- The first-life run exposed consolidation/prediction/contradiction
  amplification. Do not run longer unattended runtimes until governance,
  validation, confidence revision, and goal feedback improve.
- Global Workspace is identified as missing. Working Memory is close, but there
  is no tick-local publish/subscribe integration surface for all regions yet.
- The current CLI mock router is intentionally simple and not a reasoning
  engine.
- Local GGUF inference works, but CPU-only execution is slow. A one-model Phi-3
  run took about two minutes.
- The Desktop models folder currently contains `phi3`, `phi4`, and `qwen`.
  `llama` is configured as optional but not present.

### Recommended Next Task

Continue governance and validation:

1. Replace token-overlap prediction validation with evidence-aware validation.
2. Add provenance-preserving confidence revision records for semantic knowledge.
3. Add goal progress feedback from runtime outcomes.
4. Add relationship strengthening between repeated runtime observations.
5. Design Global Workspace as a tick-local integration surface before deeper
   runtime coupling.
