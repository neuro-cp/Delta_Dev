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
It now replaces shallow token-overlap prediction validation with a first-pass
evidence-aware evaluator that compares extracted claims, appends supported or
failed prediction revisions, and preserves validation evidence metadata.
It now adds an Evidence and Justification invariant: confidence must be derived
from evidence-backed justification, not treated as an unexplained mutable state
variable.
It now adds an evidence-derived confidence policy and append-only semantic
knowledge revision helper so justification metadata can travel with revised
knowledge without overwriting prior records.
It now adds append-only contradiction resolution: contradictions can be marked
resolved with evidence and rationale without deleting or rewriting either claim.
It now adds relationship weighting: repeated relationship evidence appends a
strengthened relationship revision with updated weight, confidence, and
reinforcement count.
It now adds prediction quality metrics over latest prediction state: evaluated
coverage, accuracy, failure rate, and average evidence score.
It now adds reflection quality scoring with explainable dimensions for whether
success, output, attention, working memory, consolidation candidates, and
repetition were observed.
It now expands the Delta Console to expose prediction quality, contradiction
state, weighted relationships, and reflection quality in the read-only
inspection surface.
It now adds a repeatable runtime experiment runner and records the first
isolated 1000-tick bounded runtime sprint.
It now adds governance stress tests and fixes the self-model so high
contradiction pressure becomes an explicit self-observation.
It now profiles runtime performance and caches simulation tokenization, reducing
the 200-tick isolated runtime comparison from `10.63` to `15.43` ticks/second.
It now begins Phase 11 hybrid inference by adding canonical inference result
types and dynamic local GGUF discovery from `G:\models`.
It now adds explicit model routing policy and append-only model observatory
records for inference latency, token counts, confidence, and model usage.
It now adds an isolated cognitive evaluation harness for repeatable cycle-level
evaluation cases.
It now adds multi-model comparison over canonical inference results, measuring
agreement, confidence spread, latency spread, and evidence counts without
treating consensus as authority.
It now expands the read-only Delta Console with model inventory, inference
observatory metrics, and recent inference events.
It now clarifies the reasoning-provider invariant: Delta integrates
capabilities under governance rather than competing providers in a leaderboard.
It now begins Phase 12 by adding a Curriculum Engine that generates directed
cognitive experience tasks, adapts difficulty from observed performance, and
marks curriculum cases as experiences rather than knowledge.
It now adds an Experience Generator and append-only Experience Store for
provider-generated observations, hypotheses, plans, simulations, predictions,
and reflections that remain pending governance.
It now adds a Capability Planner so intent maps to required cognitive
capabilities before provider allocation.
It now adds dynamic Provider Learning from inference observatory records,
deriving provider and capability profiles from observed latency, confidence,
and evidence count.
It now adds read-only Knowledge Quality reports for evidence,
counter-evidence, relationships, prediction outcomes, validation history,
revision history, derived confidence, and uncertainty.
It now adds the first World Model builder and append-only store for objects,
events, and relations extracted from governed experiences only.
It now expands the runtime experiment laboratory with structured experiment
kinds, curriculum prompt schedules, large tick target reporting, and curriculum
coverage summaries in isolated stores.
It now expands the Delta Console cognitive observatory with generated
experiences, provider effectiveness, knowledge quality, and world-model
snapshots.
It now adds read-only Knowledge Distillation reports for stable concepts, weak
concepts, and discard candidates.
It now adds Codex Mentorship reports that inspect runtime, knowledge quality,
and provider evidence to recommend engineering work without editing Delta's
cognition.
It now adds a Cognitive Benchmark comparator and CLI that separate engineering
correctness, cognitive correctness, and task performance when comparing
baseline and candidate runtime summaries.
It now records the first Phase 13 experimental validation campaign data:
curriculum runs at 100, 250, 500, and 1000 ticks using isolated stores. The
result shows stability but no measured cognitive improvement from 100 to 1000
ticks.
It now adds novelty and experience-utility measurement. The 1000-tick
curriculum run measured average novelty `0.1144`, average information gain
`0.1279`, average surprise `0.0`, average experience utility `0.1371`, and
prediction pressure rate `0.071`.
It now adds provider experience-utility profiling so future local-model runs
can compare providers by capability-local utility rather than global ranking.

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
- Reasoning providers are interchangeable cognitive components. Provider
  identity is an implementation detail; persistent memory, knowledge, evidence,
  governance, goals, and self-model state belong exclusively to Delta.
- Capability selection should precede provider selection. Delta should select
  reasoning, planning, retrieval, translation, mathematics, coding, vision,
  speech, search, or optimization capability before selecting a provider that
  can contribute it under governance.
- Provider comparison is diagnostic. It must not turn Delta into a leaderboard,
  benchmark suite, or provider-facing product.
- Curriculum tasks are experiences, not knowledge. They may feed evaluation,
  reflection, learning, evidence, and governance, but they must not directly
  create semantic knowledge.
- Generated experiences preserve provider provenance, default to pending
  governance, and explicitly forbid direct knowledge promotion.
- Capability planning precedes provider allocation. Provider routing may consume
  capability plans, but it must not replace the capability-planning step.
- Provider learning is observational evidence for future allocation, not a
  permanent preference table and not execution authority.
- Knowledge quality reports are read-only. They explain belief health without
  rewriting semantic records or promoting knowledge.
- The world model is built from governed experience. Pending generated
  experiences are ignored until governance accepts, supports, or validates them.
- Runtime laboratory reports must distinguish mechanical completion from
  cognitive quality findings.
- Console Phase 12 panels remain read-only observatory state and do not gain
  routing, validation, revision, or execution authority.
- Knowledge distillation is report-only until explicitly governed.
- Codex mentorship is an engineering workflow. It does not edit Delta cognition
  directly.
- Benchmarks must report unsupported capability questions as
  `insufficient_data` instead of guessing.
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
- Prediction validation is append-only and evidence-aware at a first-pass
  level. It compares extracted prediction claims against observation claims,
  can mark predictions as supported or failed, and records validation score,
  rationale, evidence claim, prediction claim, and observation provenance.
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
- `orchestration/tests/runtime/test_relationship_weighting.py`
- `orchestration/attention/__init__.py`
- `orchestration/attention/attention_item.py`
- `orchestration/attention/attention_service.py`
- `orchestration/cycle/__init__.py`
- `orchestration/cycle/cognitive_cycle.py`
- `orchestration/cycle/cycle_result.py`
- `orchestration/reflection/__init__.py`
- `orchestration/reflection/reflection_engine.py`
- `orchestration/reflection/reflection_record.py`
- `orchestration/tests/runtime/test_reflection_quality.py`
- `learning/region/__init__.py`
- `learning/region/learning_engine.py`
- `learning/region/learning_record.py`
- `learning/region/learning_store.py`
- `knowledge/__init__.py`
- `knowledge/consolidation_engine.py`
- `knowledge/contradiction_engine.py`
- `knowledge/contradiction_record.py`
- `orchestration/tests/runtime/test_contradiction_resolution.py`
- `knowledge/justification_engine.py`
- `knowledge/prediction_engine.py`
- `knowledge/prediction_record.py`
- `orchestration/tests/runtime/test_prediction_quality_metrics.py`
- `orchestration/tests/runtime/test_prediction_evidence_validation.py`
- `orchestration/tests/runtime/test_governance_stress.py`
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
- `tools/runtime_experiment.py`
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
- `integration/model_runtime/inference_types.py`
- `integration/model_runtime/model_registry.py`
- `integration/model_runtime/gguf_model_runner.py`
- `integration/model_runtime/routing_policy.py`
- `integration/model_runtime/model_observatory.py`
- `orchestration/tests/runtime/test_model_routing_observatory.py`
- `orchestration/evaluation/__init__.py`
- `orchestration/evaluation/cognitive_evaluation.py`
- `orchestration/tests/runtime/test_cognitive_evaluation_harness.py`
- `integration/model_runtime/model_comparison.py`
- `orchestration/tests/runtime/test_model_comparison.py`
- `orchestration/tests/runtime/test_delta_console_model_state.py`
- `tools/delta_console.py`
- `orchestration/curriculum/__init__.py`
- `orchestration/curriculum/curriculum_engine.py`
- `orchestration/tests/runtime/test_curriculum_engine.py`
- `orchestration/experience/__init__.py`
- `orchestration/experience/experience_generator.py`
- `orchestration/tests/runtime/test_experience_generator.py`
- `integration/model_runtime/capability_planner.py`
- `orchestration/tests/runtime/test_capability_planner.py`
- `integration/model_runtime/provider_learning.py`
- `orchestration/tests/runtime/test_provider_learning.py`
- `knowledge/quality_analyzer.py`
- `orchestration/tests/runtime/test_knowledge_quality.py`
- `orchestration/world_model/__init__.py`
- `orchestration/world_model/world_model.py`
- `orchestration/tests/runtime/test_world_model.py`
- `orchestration/tests/runtime/test_runtime_experiment_lab.py`
- `knowledge/distillation.py`
- `orchestration/tests/runtime/test_knowledge_distillation.py`
- `orchestration/mentorship/__init__.py`
- `orchestration/mentorship/codex_mentorship.py`
- `orchestration/tests/runtime/test_codex_mentorship.py`
- `orchestration/benchmarks/__init__.py`
- `orchestration/benchmarks/cognitive_benchmark.py`
- `orchestration/tests/runtime/test_cognitive_benchmark.py`
- `tools/cognitive_benchmark.py`
- `docs/EXPERIMENT_REPORT.md`
- `docs/BENCHMARK_RESULTS.md`
- `docs/NOVELTY_ANALYSIS.md`
- `orchestration/novelty/__init__.py`
- `orchestration/novelty/novelty_analyzer.py`
- `orchestration/tests/runtime/test_novelty_analyzer.py`
- `tools/novelty_report.py`
- `orchestration/novelty/provider_utility.py`
- `orchestration/tests/runtime/test_provider_utility.py`
- `tools/provider_utility_report.py`
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
- evidence-aware prediction validation can append supported or failed
  prediction revisions with validation metadata
- evidence-derived confidence can be computed from supporting evidence,
  counter-evidence, prediction outcomes, contradictions, and provenance
- semantic knowledge revisions append new records, preserve prior concept IDs
  in revision history, and carry justification metadata
- contradiction resolution appends resolved contradiction revisions while
  preserving both claims and the original contradiction record
- relationship strengthening appends weighted revisions and latest-state graph
  reads return the strengthened relationship
- prediction quality metrics summarize latest prediction state for self-model
  and future console inspection
- reflection records include quality metadata with a score and dimensions for
  cycle inspection
- Delta Console state includes prediction quality, latest predictions, latest
  contradictions, latest weighted relationships, reflection quality, and the
  self-model
- isolated 1000-tick runtime experiment completed successfully and produced a
  JSON summary for inspection
- governance stress tests cover duplicate consolidation suppression,
  relationship weight caps, prediction latest-state metrics, and
  contradiction-pressure self-observation
- runtime profiling identifies repeated JSONL full-store reads as the main
  remaining hot-path bottleneck after cached simulation tokenization
- local GGUF model discovery scans `G:\models`, infers family, quantization,
  context length, multimodal projector presence, and compatibility aliases
- GGUF runner output now includes canonical inference metadata while preserving
  the existing `AIOutputBundle` interface
- model routing policy prefers deterministic and local routes before optional
  cloud escalation
- model observatory records append inference metadata for later routing
  reliability analysis
- cognitive evaluation cases run through isolated stores and report route,
  success, confidence, latency, memory count, relationship count, learning
  count, stage count, and pass/fail
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

Latest evidence-aware prediction validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_prediction_evidence_validation.py orchestration\tests\runtime\test_bootstrap_runtime.py`
- result: `6 passed`
- supported case: structured prediction for `job:42` completed was supported by
  an observation saying Job #42 completed at a specific time
- failed case: structured prediction for `job:42` completed was failed by an
  observation saying Job #42 was cancelled
- bootstrap case: concept predictions still validate through evidence claim
  scoring, not the old token-overlap validation marker

Latest justification and semantic revision validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_knowledge_justification.py`
- result: `3 passed`
- evidence-derived confidence ignores the prior stored confidence value and
  derives confidence from justification inputs
- counter-evidence, failed predictions, and contradictions lower derived
  confidence
- semantic revisions append new records and become latest while preserving the
  original record in history

Latest contradiction resolution validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_contradiction_resolution.py`
- result: `2 passed`
- resolution appends a new contradiction revision with the same contradiction
  ID, both claim IDs preserved, status `resolved`, evidence IDs, and rationale
- unresolved contradictions remain open in latest-state views

Latest relationship weighting validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_relationship_weighting.py orchestration\tests\self_model\test_self_model.py`
- result: `3 passed`
- strengthened relationships preserve relationship ID, increase weight and
  confidence, increment reinforcement count, and remain append-only
- `find_equivalent` and `for_memory` resolve latest strengthened relationship
  state

Latest prediction quality metrics validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_prediction_quality_metrics.py orchestration\tests\self_model\test_self_model.py`
- result: `3 passed`
- metrics include total, open, evaluated, supported, failed, accuracy,
  coverage, failure rate, and average evidence score
- metrics resolve latest prediction revisions rather than stale historical
  records

Latest reflection quality validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_reflection_quality.py orchestration\tests\loop\test_cognitive_loop.py`
- result: `4 passed`
- rich successful reflections score higher when output, attention, working
  memory, consolidation candidates, and repeated context are present
- sparse failed reflections score low with explicit missing dimensions

Latest Delta Console validation:

- command: `.\.venv311\Scripts\python.exe -m py_compile tools\delta_console.py learning\region\learning_engine.py`
- result: passed
- command: `.\.venv311\Scripts\python.exe -c "from tools.delta_console import _state; s=_state(); print(sorted(s.keys())); print(s['prediction_quality'])"`
- result: state includes `prediction_quality`, `contradictions`,
  `relationships`, `reflection_quality`, latest stores, and self-model

Latest 1000-tick runtime validation:

- command: `.\.venv311\Scripts\python.exe tools\runtime_experiment.py --ticks 1000 --store-root .tmp\sprint8_1000 --summary-path .tmp\sprint8_1000_summary.json`
- result: `1000` requested ticks and `1000` completed ticks
- elapsed: `115.5545` seconds
- throughput: `8.6539` ticks/second
- isolated store: `.tmp\sprint8_1000`
- final counts:
  - memories: `2016`
  - relationships: `1000`
  - learning records: `1000`
  - semantic knowledge: `17`
  - contradictions: `9`
  - predictions: `22`
  - goals: `4`
- prediction quality:
  - evaluated: `15`
  - supported: `15`
  - failed: `0`
  - open: `7`
  - accuracy: `1.0`
  - coverage: `0.6818`
  - average evidence score: `0.7267`
- runtime remained mechanically stable with controlled semantic and prediction
  growth
- finding: contradiction pressure remained high (`0.5294`), and
  self-observations did not yet explain contradiction pressure as a specific
  observation

Latest governance stress validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_governance_stress.py orchestration\tests\self_model\test_self_model.py`
- result: `5 passed`
- duplicate consolidation stress: 100 duplicate learning candidates created
  only one semantic record and one prediction
- relationship weight stress: repeated strengthening capped weight and
  confidence at `1.0` while preserving reinforcement count
- prediction latest-state stress: metrics used latest prediction revision after
  many stale open revisions
- contradiction-pressure stress: self-model now emits a
  `contradiction_pressure` self-observation

Latest performance profiling validation:

- command: `.\.venv311\Scripts\python.exe -m cProfile -o .tmp\sprint10_200.prof tools\runtime_experiment.py --ticks 200 --store-root .tmp\sprint10_profile --summary-path .tmp\sprint10_200_summary.json`
- baseline profiled run: `18.663` seconds under cProfile
- baseline summary throughput: `10.6285` ticks/second
- top bottlenecks: simulation tokenization and repeated JSONL store reads
- optimization: cached `SimulationRegion._tokens` with bounded `lru_cache`
- command: `.\.venv311\Scripts\python.exe -m cProfile -o .tmp\sprint10_200_cached.prof tools\runtime_experiment.py --ticks 200 --store-root .tmp\sprint10_profile_cached --summary-path .tmp\sprint10_200_cached_summary.json`
- cached profiled run: `12.838` seconds under cProfile
- cached summary throughput: `15.4264` ticks/second
- remaining bottleneck: repeated full-store JSONL reads in memory and learning
  stores during runtime/self-model hot paths

Latest model abstraction validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_model_abstraction.py`
- result: `3 passed`
- command: `.\.venv311\Scripts\python.exe -m py_compile integration\model_runtime\model_registry.py integration\model_runtime\inference_types.py integration\model_runtime\gguf_model_runner.py`
- result: passed
- discovered local model families from `G:\models`: `phi3`, `phi4`, `qwen`,
  `llama`, `mistral`, and `ministral`
- compatibility aliases available when matching models exist: `phi3`, `phi4`,
  `qwen`, `llama`, `mistral`
- multimodal GGUF folders with `mmproj` files are marked with `vision`
  capability

Latest model routing and observatory validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_model_routing_observatory.py`
- result: `4 passed`
- deterministic math avoids model inference
- local models are preferred before cloud when available
- cloud route requires explicit permission
- observatory records model ID, route, task type, latency, token counts,
  confidence, and evidence count

Latest cognitive evaluation harness validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_cognitive_evaluation_harness.py`
- result: `2 passed`
- evaluation cases run through isolated stores
- summary output includes total, pass rate, per-category pass rate, and average
  latency

Latest multi-model comparison validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_model_comparison.py`
- result: `3 passed`
- comparison reports agreement, consensus candidate, confidence spread, latency
  spread, and evidence counts
- consensus is non-authoritative and does not replace evidence-aware validation

Latest Delta Console model observability validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_delta_console_model_state.py`
- result: `1 passed`
- console state now exposes `models`, `model_observatory`, and
  `model_inference_events`
- inference observatory metrics are read-only and do not grant model routing,
  execution, validation, or revision authority

Latest curriculum engine validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_curriculum_engine.py orchestration\tests\runtime\test_cognitive_evaluation_harness.py`
- result: `5 passed`
- curriculum cases include domain, difficulty, required capabilities, prompt,
  and explicit `direct_knowledge_promotion: false` metadata
- weak domains are prioritized and strong domains can increase difficulty
- curriculum performance can be derived from cognitive evaluation results

Latest experience generator validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_experience_generator.py orchestration\tests\runtime\test_curriculum_engine.py`
- result: `6 passed`
- provider output becomes pending generated experiences with provenance
- generated experiences cannot directly promote semantic knowledge
- unknown experience types such as `semantic_knowledge` are ignored

Latest capability planner validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_capability_planner.py orchestration\tests\runtime\test_model_routing_observatory.py`
- result: `7 passed`
- intent maps to required capabilities before provider allocation
- routing decisions preserve required capabilities in metadata
- vision-capable providers are preferred when the capability plan requires
  vision

Latest provider learning validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_provider_learning.py orchestration\tests\runtime\test_model_routing_observatory.py`
- result: `7 passed`
- provider profiles are derived from observatory records by provider/model
- capability rankings are based on observed scores, not provider names
- missing capability evidence produces no recommendation

Latest knowledge quality validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_knowledge_quality.py orchestration\tests\runtime\test_knowledge_justification.py`
- result: `5 passed`
- reports include evidence, counter-evidence, relationships, prediction
  outcomes, validation count, revision count, contradiction count, derived
  confidence, and uncertainty
- quality analysis does not mutate semantic records

Latest world model validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_world_model.py orchestration\tests\runtime\test_experience_generator.py`
- result: `6 passed`
- governed experiences can produce objects, events, and relations
- pending generated experiences are ignored
- world-model snapshots are append-only

Latest runtime experiment laboratory validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_runtime_experiment_lab.py orchestration\tests\runtime\test_curriculum_engine.py`
- result: `5 passed`
- curriculum experiments can feed curriculum prompts into runtime ticks
- reports include experiment kind, supported large tick targets, curriculum
  domain coverage, difficulty coverage, and required capability coverage
- stores remain isolated under the experiment store root

Latest cognitive observatory validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_delta_console_model_state.py orchestration\tests\runtime\test_provider_learning.py orchestration\tests\runtime\test_knowledge_quality.py`
- result: `6 passed`
- console state exposes `provider_effectiveness`, `knowledge_quality`,
  `generated_experiences`, and `world_model`
- these fields are read-only observability state

Latest knowledge distillation validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_knowledge_distillation.py orchestration\tests\runtime\test_knowledge_quality.py`
- result: `3 passed`
- stable concepts require confidence, evidence, validation, no failed
  predictions, and no contradictions
- weak and unsupported concepts are reported without deleting knowledge

Latest Codex mentorship validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_codex_mentorship.py orchestration\tests\runtime\test_knowledge_distillation.py`
- result: `3 passed`
- mentorship reports runtime incompletion, low prediction coverage, knowledge
  pressure, and missing provider evidence as engineering findings
- mentorship metadata explicitly records that it does not edit Delta cognition

Latest cognitive benchmark validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_cognitive_benchmark.py`
- result: `3 passed`
- benchmark reports separate engineering correctness, cognitive correctness,
  and task performance sections
- measured dimensions include runtime completion, prediction accuracy,
  prediction coverage, contradiction pressure, task pass rate, and API-call
  efficiency when data is supplied
- unsupported capability questions are reported as `insufficient_data`
- CLI smoke test wrote `.tmp\benchmark\report.json` from synthetic baseline and
  candidate summaries

Latest Phase 13 experience-scaling experiment:

- runs: `100`, `250`, `500`, and `1000` curriculum ticks
- store root: `.tmp\experiments\phase13\experience_scaling`
- production state: not modified
- 100 ticks: `12.3878` ticks/sec, prediction accuracy `1.0`, coverage `0.5`,
  semantic knowledge `18`, contradictions `0`
- 1000 ticks: `3.7915` ticks/sec, prediction accuracy `1.0`, coverage `0.5`,
  semantic knowledge `17`, contradictions `0`
- benchmark: `.tmp\experiments\phase13\experience_scaling\benchmark_100_vs_1000.json`
- conclusion: measured cognitive dimensions were flat while throughput
  declined; do not attempt 10,000 ticks until curriculum novelty, held-out task
  performance, and runtime hot-path costs are addressed

Latest novelty analysis:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_novelty_analyzer.py`
- result: `5 passed`
- command: `.\.venv311\Scripts\python.exe tools\novelty_report.py --store-root .tmp\experiments\phase13\experience_scaling\ticks_1000 --ticks 1000 --output-path .tmp\experiments\phase13\experience_scaling\novelty_1000.json`
- average novelty: `0.1144`
- average information gain: `0.1279`
- average surprise: `0.0`
- average experience utility: `0.1371`
- prediction pressure rate: `0.071`
- interpretation: current curriculum is domain-varied but information-poor

Latest provider utility profiling validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_provider_utility.py orchestration\tests\runtime\test_novelty_analyzer.py`
- result: `9 passed`
- provider utility profiles summarize average utility, information gain,
  surprise, prediction opportunity, and capability-specific utility
- profiles are explicitly capability evidence, not global provider rankings

Latest governance validation:

- report: `docs/GOVERNANCE_RUNTIME_REPORT.md`
- bootstrap result: `16` semantic concepts, `16` predictions, `4` goals
- runtime result: `5` requested ticks and `5` completed ticks
- semantic growth: `1` new semantic record on tick 1, `0` on ticks 2 through 5
- latest prediction state: `17` predictions, `0` open predictions after shallow
  validation
- warning: the historical governance report predates evidence-aware validation;
  current validation is first-pass claim scoring and should still not be treated
  as robust semantic entailment

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
- local models: `G:\models`
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
  update justification history, or create goals.
- Knowledge consolidation exists, but semantic confidence is not yet derived
  from a complete justification history that includes prediction
  success/failure, counter-evidence, contradictions, and provenance.
- Prediction generation exists, and prediction evaluation against future
  observations now uses first-pass evidence-aware claim scoring. It still needs
  deeper semantic entailment and broader claim extraction.
- The first-life run exposed consolidation/prediction/contradiction
  amplification. Do not run longer unattended runtimes until governance,
  validation, justification-derived confidence, and goal feedback improve.
- Global Workspace is identified as missing. Working Memory is close, but there
  is no tick-local publish/subscribe integration surface for all regions yet.
- The current CLI mock router is intentionally simple and not a reasoning
  engine.
- Local GGUF inference works, but CPU-only execution is slow. A one-model Phi-3
  run took about two minutes.
- The desktop model root is `G:\models` and currently discovers local GGUF
  families including `phi3`, `phi4`, `qwen`, `llama`, `mistral`, and
  `ministral`, with multimodal Qwen folders marked by `mmproj` vision support.

### Recommended Next Task

Continue governance and validation:

1. Do not attempt 10,000 ticks until average experience utility improves beyond
   the Phase 13 baseline.
2. Run small local-provider experience-generation experiments and profile
   providers by capability-local experience utility.
3. Replace repeated difficulty-1 curriculum templates with utility-seeking
   curriculum generation.
4. Add held-out task-performance suites for coding, research, scheduling, and
   planning.
5. Reduce repeated JSONL full-store reads in runtime hot paths.
6. Deepen prediction validation beyond first-pass evidence claim scoring.
7. Add goal progress feedback from runtime outcomes.
8. Design Global Workspace as a tick-local integration surface before deeper
   runtime coupling.

## Hardware-Aware Provider Experiments Update

Delta now has a desktop-oriented provider execution layer for constrained local
inference:

- `integration/model_runtime/provider_manager.py` keeps at most one GGUF
  provider resident at a time, unloads when switching, canonicalizes provider
  output, and can publish provider status for the console.
- `ModelSession` and `GGUFModelRunner` accept configurable GPU layer offload
  through `DELTA_N_GPU_LAYERS` or explicit manager configuration while
  preserving CPU-only default behavior.
- `ModelRoutingPolicy` now treats provider identity as an implementation
  detail, uses capability-family priors, selects local providers first, and
  permits cloud escalation only when explicitly enabled.
- `orchestration/experiments/experiment_scheduler.py` queues capability-specific
  prompts, routes them through serial provider allocation, generates pending
  experience candidates, and scores novelty, information gain, surprise, and
  experience utility.
- `tools/experiment_scheduler.py` provides the operator entrypoint for enqueueing
  and running bounded provider batches without keeping multiple local models in
  VRAM.
- `tools/delta_console.py` now exposes active provider status, GPU memory,
  experiment queue progress, and cumulative experiment utility.

Example local-provider workflow:

```powershell
.\.venv311\Scripts\python.exe tools\experiment_scheduler.py --capability planning --enqueue-defaults --provider-model phi4
.\.venv311\Scripts\python.exe tools\experiment_scheduler.py --run --limit 1 --n-gpu-layers 24
.\.venv311\Scripts\python.exe tools\delta_console.py --port 8765
```

Validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_provider_manager.py orchestration\tests\runtime\test_experiment_scheduler.py orchestration\tests\runtime\test_model_routing_observatory.py orchestration\tests\runtime\test_delta_console_model_state.py`
- result: `8 passed`
- command: `.\.venv311\Scripts\python.exe -m py_compile integration\model_runtime\provider_manager.py integration\model_runtime\model_session.py integration\model_runtime\gguf_model_runner.py integration\model_runtime\routing_policy.py orchestration\experiments\experiment_scheduler.py tools\delta_console.py tools\experiment_scheduler.py`
- result: passed

Current limitation:

- The new manager/scheduler path has regression coverage with fake providers,
  but it has not yet been characterized with real overnight `G:\models` batches.
  The next evidence step is small serial batches by capability, not a 10,000
  tick runtime.

## Provider Qualification Gate Update

Discovered local GGUF files are no longer treated as automatically usable.
Delta now has a Provider Qualification Suite that should run before any
unattended local-provider experiments.

Implemented:

- `integration/model_runtime/provider_qualification.py` probes each discovered
  model independently and never aborts the suite when one provider fails.
- For each model, the suite records load success/failure, inference
  success/failure, load time, RAM/VRAM samples, context length, quantization,
  architecture metadata when available, mmproj requirement, chat-template
  availability, first-token latency, output length, tokens/sec, and whether GPU
  memory returned near baseline after unload.
- GPU layer candidates are probed in descending order, defaulting to
  `32,28,24,22,16,8,0`; the first successful load+inference setting becomes
  `recommended_gpu_layers`.
- Reports are written to `reports/provider_qualification.json` and
  `reports/provider_qualification.md`.
- A persistent scheduler-facing capability database is written to
  `data/model_runtime/provider_capabilities.json`.
- `tools/provider_qualification.py` is the operator entrypoint.
- `tools/experiment_scheduler.py` now respects the capability database when it
  exists; unqualified pinned providers are rejected unless the operator passes
  `--ignore-qualification-db`.

Qualification command:

```powershell
.\.venv311\Scripts\python.exe tools\provider_qualification.py --model-root G:\models
```

Validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_provider_qualification.py orchestration\tests\runtime\test_experiment_scheduler.py orchestration\tests\runtime\test_provider_manager.py orchestration\tests\runtime\test_model_routing_observatory.py`
- result: `10 passed`
- command: `.\.venv311\Scripts\python.exe -m py_compile integration\model_runtime\provider_qualification.py orchestration\experiments\experiment_scheduler.py tools\provider_qualification.py tools\experiment_scheduler.py`
- result: passed
- command: `.\.venv311\Scripts\python.exe tools\provider_qualification.py --help`
- result: passed
- command: `.\.venv311\Scripts\python.exe tools\experiment_scheduler.py --help`
- result: passed

Current limitation:

- The suite has not yet been run against the real `G:\models` inventory during
  this update. Do not run unattended provider experiments until
  `reports/provider_qualification.md` and
  `data/model_runtime/provider_capabilities.json` exist from a real pass.

## Post-Qualification Experiment Sequence

After provider qualification, Delta should not jump directly into a large
autonomous run. The operational progression is:

1. Provider Smoke Test: five diagnostic prompts per qualified provider
   covering deterministic answer, explanation, JSON formatting, planning, and
   reflection.
2. Capability Calibration: bounded capability batches for planning, coding,
   mathematics, translation, summarization, reasoning, and simulation.
3. Multi-provider Disagreement: compare qualified providers on identical
   prompts and measure disagreement, surprise, and consensus evidence.
4. Curriculum Evolution: use the curriculum engine for contradiction,
   incomplete information, false assumptions, scientific reasoning, planning
   failure, ethics, and government operations prompts.
5. Long Context: only after provider context limits are known from
   qualification.
6. Reflection Loop: periodic reports asking what surprised Delta, which
   predictions failed, and which capability seems weak.
7. Curiosity Driven: prioritize expected information gain, prediction
   opportunity, belief challenge, capability gap, and surprise potential.
8. Overnight Queue: run only after the previous phases are stable.
9. Morning Report: generate provider, cognitive, learning, and engineering
   reports.

`tools/experiment_scheduler.py --enqueue-provider-smoke` now queues Phase 1
diagnostic prompts for every provider marked qualified in
`data/model_runtime/provider_capabilities.json`.

## Local Provider Integration Baseline

The provider work has moved from qualification into integrated Delta smoke
testing.

CUDA/backend status:

- The `.venv311` environment now imports CUDA-backed `llama-cpp-python`
  successfully.
- The missing CUDA runtime dependencies were resolved by installing the venv
  NVIDIA runtime packages for CUDA 12 and registering their `bin` directories
  through `.venv311\Lib\site-packages\sitecustomize.py`.
- A Windows loader issue in the installed `llama_cpp` package was corrected so
  `llama.dll` can resolve `ggml-cuda.dll` dependencies.
- Direct checks confirmed `llama.dll` loads, `llama_cpp` imports, and GGUF
  inference allocates multiple GB of VRAM.

Qualified backend-validated provider pool:

| Provider | GPU layers | Tokens/sec | Peak VRAM |
| --- | ---: | ---: | ---: |
| Llama 3.1 8B Q4_K_M | 36 | 15.9165 | 6639 MB |
| Mistral 7B Q4_K_M | 36 | 15.5774 | 6420 MB |
| Phi-3.1 Mini Q4_K_M | 36 | 16.166 | 4822 MB |
| Qwen2.5 7B Q4_K_M | 36 | 15.5569 | 5849 MB |

The capability database at
`data/model_runtime/provider_capabilities.json` now marks those four providers
as qualified and backend validated, with `recommended_gpu_layers = 36`.
CPU utilization remains intentionally unblocked/unknown because VRAM movement
and throughput already prove GPU offload.

Provider integration changes:

- `ProviderManager` now reads `recommended_gpu_layers` from the capability
  database when no explicit override is supplied.
- `ProviderManager` passes both `prompt` and `question` across the model
  boundary. This fixes a real boundary-preservation bug where local providers
  received the wrapper prompt but not the actual task question expected by the
  prompt builder.
- `DELTA_MAX_TOKENS` can cap local generations for smoke and calibration runs.
- `tools/provider_smoke_report.py` regenerates
  `reports/provider_smoke_report.json` and
  `reports/provider_smoke_report.md` from scheduler JSONL state.

Corrected provider smoke run:

- run id: `provider_smoke_20260701T035235Z`
- completed: `28/28`
- generated experience candidates: `112`
- average utility: `0.43`
- average information gain: `0.384`
- average surprise: `0.0804`

Provider utility in the corrected smoke run:

| Provider | Count | Utility | Info Gain | Surprise |
| --- | ---: | ---: | ---: | ---: |
| Llama 3.1 8B Q4_K_M | 7 | 0.4366 | 0.3886 | 0.0714 |
| Mistral 7B Q4_K_M | 7 | 0.4392 | 0.3949 | 0.1071 |
| Phi-3.1 Mini Q4_K_M | 7 | 0.4211 | 0.3752 | 0.0714 |
| Qwen2.5 7B Q4_K_M | 7 | 0.4232 | 0.3773 | 0.0714 |

Capability utility in the corrected smoke run:

| Capability | Count | Utility | Info Gain | Surprise |
| --- | ---: | ---: | ---: | ---: |
| Coding | 4 | 0.6391 | 0.5854 | 0.25 |
| Reflection | 4 | 0.5113 | 0.471 | 0.25 |
| Reasoning | 4 | 0.3998 | 0.3552 | 0.0625 |
| Explanation | 4 | 0.3754 | 0.3282 | 0.0 |
| Planning | 4 | 0.3754 | 0.3282 | 0.0 |
| JSON | 4 | 0.3719 | 0.3265 | 0.0 |
| Deterministic | 4 | 0.3372 | 0.2935 | 0.0 |

Interpretation:

- The local provider path is operational enough to leave benchmark mode and
  begin capability calibration.
- The first corrected smoke run is not evidence that Delta learned; it is
  evidence that provider allocation, inference, experience generation, novelty
  scoring, and report generation work together.
- Surprise is present but weak and concentrated in coding/reflection prompts.
  The next curriculum should intentionally introduce contradiction, belief
  challenge, incomplete evidence, and failed expectations.
- Provider ranking should remain capability-local. Mistral had the highest
  average smoke utility in this tiny run, but the sample is too small for a
  global provider preference.

Validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_provider_manager.py orchestration\tests\runtime\test_experiment_scheduler.py orchestration\tests\runtime\test_experiment_scheduler_cli.py orchestration\tests\runtime\test_model_routing_observatory.py orchestration\tests\runtime\test_provider_qualification.py`
- result: `12 passed`
- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_provider_manager.py orchestration\tests\runtime\test_experiment_scheduler.py orchestration\tests\runtime\test_experiment_scheduler_cli.py`
- result: `6 passed`
- command: `.\.venv311\Scripts\python.exe -m py_compile integration\model_runtime\provider_manager.py integration\model_runtime\model_session.py tools\experiment_scheduler.py tools\provider_backend_benchmark.py tools\provider_smoke_report.py`
- result: passed

## Phase 14 Cognitive Calibration

Infrastructure work is frozen unless an experiment exposes a missing feature.
The next question is whether Delta receives better cognitive pressure from
better experiences.

Implemented:

- `orchestration/curriculum/calibration_curriculum.py` adds a
  `CalibrationCurriculumGenerator` for high-pressure experiment objectives.
- Calibration objectives target prediction error, contradiction resolution,
  belief revision, planning failure, transfer learning, and cross-domain
  reasoning.
- Objectives are selected with the existing novelty analyzer using novelty,
  information gain, prediction opportunity, belief challenge, surprise, and
  diversity.
- `tools/experiment_scheduler.py --enqueue-calibration` queues selected
  calibration objectives across every qualified provider.
- `tools/provider_smoke_report.py` now supports custom titles and objective
  breakdowns, so the same report path can summarize smoke and calibration
  runs.
- `docs/CURRICULUM_ANALYSIS.md` records curriculum results.
- `docs/PROVIDER_CAPABILITIES.md` records provisional provider specialization
  evidence.

Calibration run:

- command: `$env:DELTA_MAX_TOKENS='192'; .\.venv311\Scripts\python.exe tools\experiment_scheduler.py --enqueue-calibration --calibration-count 8 --run --limit 32`
- run id: `calibration_20260701T040306Z`
- completed: `32/32`
- generated experience candidates: `128`
- average utility: `0.6081`
- average information gain: `0.5525`
- average surprise: `0.2422`

Comparison with provider smoke baseline:

| Run | Utility | Information Gain | Surprise |
| --- | ---: | ---: | ---: |
| Provider smoke | 0.43 | 0.384 | 0.0804 |
| Cognitive calibration | 0.6081 | 0.5525 | 0.2422 |

Preliminary provider evidence from this run:

| Provider | Utility | Information Gain | Surprise |
| --- | ---: | ---: | ---: |
| Qwen2.5 7B Q4_K_M | 0.6702 | 0.6087 | 0.3063 |
| Phi-3.1 Mini Q4_K_M | 0.6104 | 0.5578 | 0.2625 |
| Llama 3.1 8B Q4_K_M | 0.5919 | 0.5378 | 0.1875 |
| Mistral 7B Q4_K_M | 0.5599 | 0.5056 | 0.2125 |

Interpretation:

- Better curriculum selection produced a clear improvement in experience
  utility and surprise without changing provider infrastructure.
- This is evidence that the prior bottleneck was experience quality, not local
  inference plumbing.
- The result is not yet evidence of durable learning because generated
  experiences remain candidates pending downstream governance and knowledge
  ingestion.
- Provider specialization should remain provisional until larger
  capability-specific batches are run.

Validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_curriculum_engine.py orchestration\tests\runtime\test_experiment_scheduler.py orchestration\tests\runtime\test_experiment_scheduler_cli.py`
- result: `8 passed`
- command: `.\.venv311\Scripts\python.exe -m py_compile orchestration\curriculum\calibration_curriculum.py tools\experiment_scheduler.py tools\provider_smoke_report.py`
- result: passed

## Governed Local-Provider Training

The project has moved from provider characterization into operation. A new
bounded operator command runs `CognitiveRuntime` cycles through local GGUF
providers using the Phase 14 calibration objectives.

Implemented only because the run path was blocked:

- `tools/governed_training_run.py` connects existing `CognitiveRuntime`,
  `CognitiveLoop`, `ProviderManager`, semantic consolidation, prediction
  validation, self-model generation, and calibration objectives.
- The tool uses the current provisional capability-provider hints:
  prediction/planning/cross-domain through Qwen2.5, contradiction through
  Mistral, and transfer through Llama.
- No new cognitive region or analyzer was added.

Concrete blocker found during shakedown:

- Initial 12-cycle run created `+61` contradictions from only `+3` semantic
  knowledge growth.
- Cause: recent learning records were reconsolidated repeatedly, and
  contradiction detection treated long prompts with negation terms as
  contradictory to broad foundational concepts.

Narrow fixes:

- `SemanticConsolidationEngine` now skips learning IDs that have already been
  represented in semantic knowledge.
- `ContradictionEngine.add_all()` now avoids duplicate open contradiction pairs.
- `ContradictionEngine.detect_for()` now requires meaningful content-token
  overlap, not just opposing negation and a few shared common terms.

Post-fix shakedown:

- cycles: `12/12`
- contradictions: `+5`
- semantic knowledge: `+3`
- predictions: `+6`
- prediction coverage: `0.9545`
- prediction accuracy: `1.0`

50-cycle governed training run:

- command: `$env:DELTA_MAX_TOKENS='160'; .\.venv311\Scripts\python.exe tools\governed_training_run.py --cycles 50 --objective-count 8 --store-root data\training\phase14_governed_50 --summary-path reports\phase14_governed_training_50.json`
- run id: `governed_training_20260701T042214Z`
- report: `reports/phase14_governed_training_50.md`
- cycles completed: `50/50`
- memories: `+100`
- relationships: `+50`
- learning records: `+50`
- semantic knowledge: `+1`
- predictions: `+8`
- contradictions: `+12`
- final prediction coverage: `0.9583`
- final prediction accuracy: `1.0`

Interpretation:

- Delta can now operate through local-provider governed training cycles.
- The next bottleneck is not provider infrastructure or curriculum selection.
  It is semantic candidate quality: learning records are active, but durable
  knowledge formation is weak because candidates remain too generic.
- Do not scale to 250+ cycles until learning extracts concrete claims from
  provider output, evidence, and reflection.

Validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_governance_stress.py orchestration\tests\runtime\test_contradiction_resolution.py`
- result: `8 passed`
- command: `.\.venv311\Scripts\python.exe -m py_compile knowledge\consolidation_engine.py knowledge\contradiction_engine.py tools\governed_training_run.py`
- result: passed

## Semantic Extraction Follow-Up

The 50-cycle governed training run showed that Delta was operating but not
abstracting enough durable knowledge. The concrete bottleneck was in the
existing `LearningEngine`: successful provider output was not being converted
into reusable semantic candidates unless attended context repeated.

Implemented:

- `LearningEngine` now extracts reusable semantic candidates from successful
  provider outputs.
- Candidate extraction looks for claim-like sentences involving prediction,
  evidence, confidence, uncertainty, contradiction, risk, falsification, or
  conditional reasoning.
- The old repeated-attended-context candidate remains only as a fallback when
  no reusable output claim is available.
- Regression tests verify that provider-output claims become semantic
  candidates and that repeated context remains a fallback.

Semantic extraction run:

- command: `$env:DELTA_MAX_TOKENS='160'; .\.venv311\Scripts\python.exe tools\governed_training_run.py --cycles 50 --objective-count 8 --store-root data\training\phase14_governed_50_semantic_extraction --summary-path reports\phase14_governed_training_50_semantic_extraction.json`
- run id: `governed_training_20260701T042836Z`
- report: `reports/phase14_governed_training_50_semantic_extraction.md`
- cycles completed: `50/50`

Comparison with previous 50-cycle governed run:

| Metric | Previous | Semantic extraction |
| --- | ---: | ---: |
| Memories | +100 | +100 |
| Relationships | +50 | +50 |
| Learning records | +50 | +50 |
| Semantic knowledge | +1 | +19 |
| Predictions | +8 | +19 |
| Contradictions | +12 | 0 |
| Learning efficiency | 0.34 | 0.70 |
| Knowledge stability | 0.2941 | 1.0 |

Interpretation:

- Semantic extraction materially improved durable knowledge growth at the same
  50-cycle scale.
- The next bottleneck is prediction validation backlog: richer semantic
  knowledge generated more predictions, leaving `20` open predictions at run
  end.
- The next scale test should be 100 governed cycles, not 250+, and should track
  whether open predictions accumulate faster than validation can resolve them.

Validation:

- command: `.\.venv311\Scripts\python.exe -m pytest orchestration\tests\runtime\test_reflection_quality.py orchestration\tests\runtime\test_governance_stress.py orchestration\tests\runtime\test_contradiction_resolution.py`
- result: `13 passed`
- command: `.\.venv311\Scripts\python.exe -m py_compile learning\region\learning_engine.py knowledge\consolidation_engine.py knowledge\contradiction_engine.py tools\governed_training_run.py`
- result: passed

## 100-Cycle Semantic Extraction Gate

The 100-cycle governed training pass was run after semantic extraction improved
50-cycle durable knowledge formation.

Run:

- command: `$env:DELTA_MAX_TOKENS='160'; .\.venv311\Scripts\python.exe tools\governed_training_run.py --cycles 100 --objective-count 8 --store-root data\training\phase14_governed_100_semantic_extraction --summary-path reports\phase14_governed_training_100_semantic_extraction.json`
- run id: `governed_training_20260701T043112Z`
- report: `reports/phase14_governed_training_100_semantic_extraction.md`
- cycles completed: `100/100`
- memories: `+200`
- relationships: `+100`
- learning records: `+100`
- semantic knowledge: `+19`
- predictions: `+19`
- contradictions: `0`
- open predictions: `20`

Interpretation:

- Semantic extraction remained stable and contradiction-safe.
- The repeated objective set saturated: 100 cycles produced the same latest
  semantic knowledge growth as the 50-cycle semantic extraction run.
- Open prediction backlog stayed stable at `20`; it did not explode from 50 to
  100 cycles.
- The next bottleneck is objective diversity and explicit outcome observations,
  not raw cycle count.

Next gate:

- Generate a larger non-repeating objective set.
- Include outcome observations for open predictions.
- Compare 50 diverse cycles against this repeated-objective 100-cycle result.
