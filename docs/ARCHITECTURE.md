# DELTA Architecture

## What Delta Is

Delta is a persistent cognitive substrate. Its purpose is to accumulate
experience, organize knowledge, form relationships, allocate attention, reason,
act, evaluate outcomes, and improve its internal organization over time.

Delta is not a chatbot, an LLM wrapper, or a loose collection of utilities.
External AI models are plugins and interpretive surfaces. They may assist the
cycle, but they must not become hidden authority inside the substrate.

## Cognitive Substrate

The substrate is the persistent state and service architecture that allows
Delta to continue across sessions. It includes memory, relationships,
attention, goals, reflection, learning, and execution boundaries.

The substrate must be:

- persistent across runs
- inspectable
- modular
- explicit about authority
- capable of accumulating experience without silently mutating core behavior

## Canonical Cognitive Cycle

Delta evolves around this cycle:

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
Observe
```

Not every stage is fully implemented yet. However, every new subsystem should
identify where it receives information from the cycle and where it contributes
back into the cycle.

## Memory Layers

Delta uses layered memory. These layers should remain conceptually separate
even when early implementations share storage mechanics.

### Experience Memory

Immutable raw observations, actions, outputs, documents, conversations, sensor
events, and operator notes. This is the autobiographical substrate.

### Semantic Memory

Consolidated knowledge derived from repeated or trusted experiences. Semantic
memory may change over time through explicit consolidation and evidence-backed
justification updates. Confidence should be derived from that justification,
not silently mutated as standalone state.

### Episodic Memory

Linked sequences of experiences. Episodic memory preserves temporal context:
what happened, in what order, under what conditions, and with what result.

### Working Memory

Temporary active cognition: current prompt, active goals, attended context,
reasoning state, and transient hypotheses. Working memory is not the durable
source of truth.

## Canonical Regions

Regions are services with explicit state and interfaces, not hard-coded brain
analogies.

- Memory Region: owns experience, semantic, episodic, and working memory.
- Relationship Region: records links such as temporal sequence, similarity,
  contradiction, dependency, hierarchy, causality, and reinforcement.
- Attention Region: ranks what matters now. Attention is not retrieval.
- Reasoning Region: transforms attended context into conclusions.
- Planning Region: selects possible future actions.
- Goal Region: tracks active objectives and priorities.
- Agency Region: proposes what Delta should do next from goals, planning,
  simulation, self-model, and confidence signals without executing.
- Executive Controller: prioritizes goals and allocates cognitive focus without
  replacing attention or execution.
- Learning Region: proposes durable changes from experience.
- Execution Region: performs bounded actions through explicit authorization.
- Reflection Region: evaluates what changed, repeated, failed, or should be
  consolidated.
- Self Model Region: derives Delta's current capabilities, limitations,
  metrics, health, and temporal continuity from existing regions.
- Simulation Region: evaluates hypothetical futures without executing,
  planning, or mutating state.

## Interface Principles

Every subsystem should:

- own its state
- expose explicit interfaces
- participate in the cognitive cycle
- be independently replaceable
- avoid direct hidden mutation of other regions
- return structured outputs where possible

## Interface Surface Principle

Delta may expose many interfaces over time: conversation, coding, automation,
robotics, dashboards, APIs, and future embodied inputs.

These interfaces are clients of the substrate. They are not the substrate
itself.

Never optimize the architecture around a single interface. Conversation is one
possible surface over Delta's cognition, not the organizing principle of Delta.

## Reasoning Provider Principle

External and local models are reasoning providers, not the substrate.

Delta receives canonical inference results with model identity, provider,
answer, raw output, confidence, latency, token counts, evidence, and metadata.
The substrate must not depend on whether an answer came from Phi, Qwen, Llama,
GPT, a mock provider, or a future provider.

Models propose. Delta evaluates, validates, governs, and revises knowledge.

Provider identity is an implementation detail. Persistent memory, knowledge,
evidence, governance, goals, and self-model state belong exclusively to Delta,
not to Phi, Qwen, Llama, GPT, or any future reasoning provider.

Delta should perform capability selection before provider selection. It should
ask what the current cognitive task requires, such as reasoning, planning,
retrieval, translation, mathematics, coding, vision, speech, search, or
optimization, then route to one or more providers only when those providers can
contribute useful capability under governance.

The Capability Planner records this decision explicitly. A provider route may
consume a capability plan, but it must not replace one. Provider allocation is
an implementation detail of capability planning.

Routing policy is explicit: deterministic routes avoid provider inference,
local providers are preferred before cloud providers, and cloud use requires
explicit permission. Inference events are recorded through an append-only
observatory store with provider, model ID, route, task type, latency, token
counts, confidence, and evidence count. The observatory is an inference
observatory, not an LLM-only model tracker, because future providers may include
symbolic solvers, planners, search, vision, OCR, robotics, or external APIs.

Provider learning is derived from inference observatory records. It may profile
latency, confidence, evidence count, and capability-specific effectiveness, but
it must not create permanent hardcoded provider preferences. Provider learning
is evidence for future allocation, not authority.

Multi-model comparison measures agreement, confidence spread, latency spread,
and evidence availability across canonical inference results. Consensus is
non-authoritative: it can summarize agreement, but it must not override
evidence validation, provenance, contradiction handling, or governance.
Provider comparison is diagnostic. Delta is not a leaderboard, benchmark suite,
or provider-facing product.

Cognitive evaluation is separate from benchmarking. Evaluation cases run through
isolated stores and measure cycle behavior such as route, success, confidence,
latency, memory creation, relationship creation, learning records, and stage
coverage.

The Delta Console is a read-only observability surface. It may display model
inventory, inference observatory metrics, and recent inference events, but it
must not route, execute, validate, or revise knowledge on its own.
It may also display generated experiences, provider effectiveness, knowledge
quality, and world-model snapshots as observatory state only.

Runtime laboratory experiments must use isolated stores. Structured experiment
kinds may feed curriculum prompts into runtime ticks, but the resulting reports
must distinguish mechanical completion from cognitive quality findings.

## Benchmark Principle

Progress should be measured as capability change over experience, not subsystem
count.

Benchmark reports must separate:

- engineering correctness: tests pass, runtimes complete, stores remain
  consistent
- cognitive correctness: prediction accuracy, prediction coverage,
  contradiction pressure, calibration, evidence quality, and belief stability
- task performance: coding, research, scheduling, planning, analysis, and other
  domain outcomes improve on held-out tasks

If a benchmark dimension lacks evidence, report `insufficient_data` rather than
guessing. A benchmark should be able to compare 100, 1,000, 10,000, and larger
experience runs and answer whether Delta became more capable, not merely larger.

## Curriculum Principle

Delta should receive directed experience, not random inference.

The Curriculum Engine generates structured cognitive tasks across domains such
as arithmetic, logic, causal reasoning, abstraction, planning, scheduling,
contradiction, prediction, uncertainty, language, software engineering,
scientific reasoning, government workflows, and research methodology.

Curriculum tasks are experiences, not knowledge. They may enter evaluation,
reflection, learning, evidence, and governance pipelines, but they must not
directly create semantic knowledge or bypass provenance requirements.

Curriculum difficulty should adapt from observed performance. Weak domains
should receive more practice. Strong domains may increase difficulty.

## Experience Generation Principle

Reasoning providers may generate candidate experiences, not knowledge.

Generated experiences may include observations, hypotheses, plans, simulations,
predictions, and reflections. Each generated experience must preserve provider
provenance, remain pending governance by default, and explicitly forbid direct
knowledge promotion.

Generated experiences enter the existing evidence and governance pipeline.
Only governed evidence can later support semantic knowledge, prediction
validation, contradiction resolution, or confidence revision.

## World Model Principle

The world model is built from governed experience, not provider assertion.

World-model records may represent objects, events, and relationships such as
mentions, dependencies, causes, effects, agents, actions, states, and time. The
first implementation extracts objects, events, and mention relations from
accepted, supported, or validated experiences only.

Pending generated experiences must not enter the world model until governance
accepts them.

## Attention Principle

Attention is not retrieval.

Retrieval answers: what exists?

Attention answers: what matters right now?

Attention may use retrieved memory as one input, but it should also account for
recency, confidence, novelty, contradiction, goal relevance, task relevance,
operator priority, salience, and future nervous-system signals.

## Evidence Principle

Evidence is the currency of durable cognition.

Knowledge promotion, prediction validation, contradiction resolution, self-model
assessment, and confidence revision must be justified by evidence. Confidence is
a derived summary of supporting evidence, counter-evidence, validation history,
contradiction pressure, and provenance.

Delta should always be able to answer: what evidence changed this belief?

## Authority Principles

- Raw memory has no execution authority.
- Model output has no execution authority.
- Reflection has no execution authority.
- Learning proposals have no execution authority until explicitly promoted.
- Execution requires explicit bounded interfaces.
- Inspection and audit surfaces remain read-only.

## Current Architecture Status

Implemented early:

- CLI developer entrypoint
- orchestration loop
- mock and real model plugin routes
- append-only persistent experience memory
- first cognitive cycle wrapper
- relationship records for cycle links
- simple attention ranking over recalled memory
- attended memory context forwarded into orchestration as advisory metadata
- structured reflection records
- reflection quality metadata scoring whether success, output, attention,
  working memory, consolidation candidates, and repetition were observed
- non-authoritative Learning Region records
- cycle-attached learning stage producing semantic candidates, confidence
  update suggestions, questions, and goal candidates
- semantic knowledge records with provenance
- explicit semantic consolidation from learning records
- contradiction records for preserved conflicting claims
- prediction records generated from sufficiently confident knowledge
- evidence-aware prediction validation through append-only supported or failed
  prediction revisions
- per-cycle working memory context assembled from observation, attention,
  semantic knowledge, and predictions
- generated self-model snapshots with temporal continuity, cognitive metrics,
  and health indicators
- self-model observations for contradiction pressure, prediction evaluation
  gaps, learning without consolidation, and memory fragmentation
- non-executing simulation reports over hypothetical futures
- append-only goal records
- proposed plans that survive across sessions
- explicit decision records for proposed plans
- agency proposals that answer what Delta should do next without execution

## Runtime V2.8 Validation Surface

Runtime V2.8 adds a validation and hardening layer over the current local
runtime scaffold. It is not a new authority path.

The validated local pipeline is:

```text
ask
-> unknown detection
-> retrieval
-> evidence
-> provider advisory
-> evaluator
-> candidate memory
-> approval gate
-> recall
-> synthesis
```

Runtime V2.8 also adds deterministic failure injection, fixture-only stress
testing, observability dashboards, architecture-audit recommendations, and
expanded regression coverage. All V2.8 work remains report/test oriented.

V2.8 does not enable training, model artifact creation, provider authority,
HYB1 promotion, scheduler/background workers, action execution, autonomous
memory mutation, or authoritative recall.

Incomplete:

- applied goal evolution from learning/reflection
- completed plan execution histories
- action beyond returning orchestration output
- derived confidence from evidence-backed justification history
- deeper semantic prediction validation beyond first-pass claim scoring
- durable attention state
- scheduled consolidation
- simulation feedback into prediction evaluation and planning
- live visual and auditory input
- regulable nervous-system signals

## Working Memory

Working memory is the temporary active context for one cognitive cycle. It is
assembled, inspected by reflection, and then discarded.

Current working memory inputs:

- current observation
- attended experience memories
- related semantic knowledge
- open predictions

Working memory is advisory context. It does not persist as truth and has no
execution authority.

## Self Model

The Self Model is a derived region, not an authoritative region. It must not
become another persistent database of facts.

Every Self Model field should be computed from existing regions whenever
possible. If information already exists elsewhere, the Self Model should
reference or summarize it rather than duplicate it.

Current Self Model outputs:

- current capabilities and limitations
- knowledge coverage
- confidence distribution
- prediction status and accuracy when outcomes exist
- contradiction pressure
- recent learning
- temporal continuity across today, the last seven days, and full history
- subsystem health
- cognitive health indicators
- structured self-observations generated from metrics

Self-observations are generated report outputs. They are not semantic knowledge
and have no execution authority.

## Simulation

Simulation is not execution and is not planning.

The Simulation Region evaluates hypothetical futures using working memory,
semantic knowledge, relationships, predictions, and goals when available. It
returns hypothetical outcomes, confidence estimates, risks, supporting evidence
references, and rationale.

Planning may eventually consume simulation reports. Simulation itself must not
choose actions, mutate state, or bypass the cognitive cycle.

Simulation tokenization is cached as a bounded performance optimization. This
does not change simulation authority or persistence.

## Agency

Agency answers: what should Delta do next?

Agency owns no knowledge and has no hidden execution authority. It consumes
goals, planning, simulation, confidence, attention outputs, self-model signals,
and working memory when available. It returns inspectable proposals only.

Current Agency implementation:

- persistent append-only goal records
- executive goal prioritization
- non-executing plan generation from goals and simulation
- explicit decision records that score expected reward, goal satisfaction,
  confidence, resource cost, and risk
- intrinsic virtual goals derived from self-model observations when no
  persistent goals exist

Agency determines what deserves action. Attention determines what deserves
thought. Planning determines how action might proceed. Execution determines
what actually happens through bounded interfaces.

Agency proposals, plans, and decisions do not execute automatically.

## Knowledge Layer

Knowledge is not raw memory. Knowledge is consolidated semantic structure
derived from experience, relationships, reflection, and learning records.

Current knowledge implementation:

- semantic knowledge records are stored separately from autobiographical memory
- every semantic record preserves supporting evidence and creation source
- revisions append new records rather than overwriting old records
- contradictions preserve both claims and link them through contradiction records
- contradiction resolution appends a resolved contradiction revision with
  evidence and rationale; it never deletes either claim
- predictions are generated from sufficiently confident semantic records
- prediction validation compares extracted claims against later evidence,
  preserves supporting or failing observation IDs, and records an evidence score
  on the appended prediction revision
- prediction quality metrics summarize latest prediction state, including
  evaluated coverage, accuracy, failure rate, and average evidence score
- confidence should become a consequence of evidence, validation history,
  contradictions, and provenance rather than a manually updated field
- semantic knowledge revisions are append-only records that preserve the prior
  concept ID in `revision_history` and carry justification metadata explaining
  derived confidence
- relationship records carry confidence, weight, and reinforcement count;
  repeated evidence strengthens relationships through append-only revisions
- knowledge quality reports summarize evidence, counter-evidence,
  relationships, prediction outcomes, validation history, revision history,
  derived confidence, and uncertainty without mutating semantic records

Knowledge has no direct execution authority.

Knowledge distillation is report-only until explicitly governed. Distillation
may identify stable concepts, weak concepts, and discard candidates from
knowledge quality reports, but it must not promote, delete, or rewrite
knowledge automatically.

Codex mentorship is an engineering workflow, not a cognition editor. Codex may
inspect runtime reports, knowledge quality, contradiction pressure, provider
allocation, and observatory evidence, then propose architecture or governance
work. Codex must not directly edit Delta's memories, beliefs, goals, or
self-model as if they were its own cognition.

## Reasoning Provider Runtime

Reasoning providers are interchangeable cognitive components. Delta's objective
is not to expose provider identity to the user or crown a single winner, but to
integrate provider capabilities under one governed cognitive substrate.

Provider identity is an implementation detail. Persistent memory, knowledge,
evidence, governance, goals, runtime history, and the self-model belong to
Delta.

Current provider runtime implementation:

- local GGUF models are discovered dynamically from `G:\models`
- discovered models are not assumed usable until the Provider Qualification
  Suite proves load, inference, unload, and memory-return behavior
- capability planning happens before provider allocation
- routing uses capability-family priors and local providers before cloud
  escalation
- cloud providers are allowed only when explicitly enabled and no suitable
  local provider is available
- `ProviderManager` keeps at most one local provider resident at a time
- provider load/unload state can be published for console observation
- GPU layer offload is controlled by `DELTA_N_GPU_LAYERS`, explicit manager
  configuration, or the empirical recommendation stored in
  `data/model_runtime/provider_capabilities.json`
- the experiment scheduler runs capability-specific queues through serial
  provider allocation and scores generated experiences for utility,
  information gain, and surprise
- when `data/model_runtime/provider_capabilities.json` exists, experiment
  scheduling uses only qualified providers unless the operator explicitly
  overrides the qualification gate

The provider manager and scheduler are infrastructure. They do not own
knowledge, validate truth, or promote generated text. All generated experiences
must still pass through evidence and governance before knowledge formation.

Calibration curriculum generation is also infrastructure, not a cognitive
region. It designs higher-pressure experiences and rejects low-value prompts
before scheduling. It may optimize for novelty, information gain, surprise,
prediction opportunity, belief challenge, transfer, and cross-domain reasoning,
but it does not promote provider output into knowledge.

Provider qualification writes:

- `reports/provider_qualification.json`
- `reports/provider_qualification.md`
- `data/model_runtime/provider_capabilities.json`

The capability database is empirical hardware evidence for the current desktop.
It should be regenerated after changing models, llama.cpp builds, GPU drivers,
or offload policy.

Current desktop baseline:

- CUDA-backed `llama-cpp-python` is operational through the `.venv311`
  environment.
- Four text providers are qualified and backend validated on the RTX 3060
  12 GB: Llama 3.1 8B Q4_K_M, Mistral 7B Q4_K_M, Phi-3.1 Mini Q4_K_M, and
  Qwen2.5 7B Q4_K_M.
- The empirical offload recommendation for those four providers is
  `recommended_gpu_layers = 36`.
- The experiment scheduler consumes the capability database when allocating
  local providers and records utility, information gain, and surprise for the
  generated experience candidates.
- The first corrected integrated provider smoke run is recorded in
  `reports/provider_smoke_report.md`.

## Non-Negotiable Design Rule

Do not build isolated intelligence modules. Every new subsystem must participate
in the canonical cognitive cycle through well-defined interfaces. If a subsystem
cannot identify where it receives information from the cycle and where it
contributes back into the cycle, reconsider its design.

## Runtime ARC I Cognitive Kernel

Runtime ARC I adds an orchestration-only Cognitive Kernel above the current
runtime scaffolds. The kernel coordinates managers for experience, evidence,
recall, reasoning, learning, review, integration, and safety. It centralizes
routing, event flow, state snapshots, transaction lifecycle records, audit graph
links, capability registry lookup, and dynamic pipeline assembly.

The kernel is not a new authority source. It does not train, call providers,
mutate memory, mutate recall, execute actions, start schedulers, promote HYB1,
or change Model B defaults. Its purpose is cohesion: every cognitive operation
should become inspectable through kernel events, runtime state, transactions,
audit graph links, and safety checks before future substrate work begins.

## Runtime ARC II Knowledge Substrate

Runtime ARC II defines DELTA's internal semantic substrate. It is not document
storage, RAG, training, or provider integration. It introduces reviewable
knowledge objects for entities, concepts, observations, evidence, sources,
relationships, events, claims, hypotheses, procedures, and rules.

Every ARC II knowledge object carries provenance, confidence, review state,
audit id, and rollback token. Registries and the graph builder are deterministic
and non-authoritative. Semantic queries can inspect related concepts,
supporting evidence, contradictions, procedures, and observations, but ARC II
does not perform reasoning over those results.

ARC II performs no live persistence, no canonical memory mutation, no recall
mutation, no provider authority, no training, no action execution, no scheduler
activation, and no live knowledge integration.

## Runtime ARC III Reasoning Layer

Runtime ARC III introduces deterministic, transient reasoning over the ARC II
Knowledge Substrate. It builds reasoning contexts, session-only reasoning
graphs, hypotheses, evidence chains, contradiction presentations, confidence
propagation, alternative paths, counterfactual branches, goal-constrained
deliberation, explanation trees, reflection passes, self-consistency checks, and
reasoning transactions.

Reasoning is temporary. Knowledge is durable. Hypotheses are not facts. ARC III
never mutates the substrate, promotes hypotheses, writes memory, calls
providers, starts schedulers, trains models, or executes actions.

## Runtime ARC IV Knowledge Evolution

Runtime ARC IV determines whether reasoning should influence future knowledge.
It introduces simulation-only knowledge evolution through explicit governance:
integration candidates, version graphs, simulations, impact analysis,
contradiction workflows, multi-reviewer records, knowledge health metrics,
controlled integration transactions, rollback plans, evolution timelines,
diffs, and evaluation estimates.

ARC IV stops at `ready_to_integrate`. It does not perform live integration,
training, provider authority, scheduler activation, action execution, hidden
writes, autonomous memory, or knowledge mutation. Every future mutation must be
explicit, reviewed, rollback-capable, and fully audited.

## Runtime ARC VI Executive Cognition

Runtime ARC VI adds an executive cognition layer for goal-oriented
orchestration. The executive layer creates planning-only `ExecutiveGoal`
objects, decomposes them into tasks, selects candidate capabilities, estimates
resources, builds deliberation plans, checks constraints, requests escalation,
simulates multi-goal ordering, reflects on plans, and produces executive audit
records.

The executive layer coordinates cognition; it does not perform cognition as an
authority source. It does not reason directly, execute actions, call providers,
start schedulers, train models, mutate memory, mutate knowledge, promote HYB1,
or change Model B defaults. ARC VI's decision graphs and transactions are
transient planning artifacts.

## Runtime ARC VII-XXV Cognitive Runtime Scaffolds

Runtime ARC VII through ARC XXV add deterministic architecture scaffolds for
collaborative investigation, advisory specialists, governed evidence
acquisition, controlled tool/provider interfaces, integration previews,
evaluation, replay, domain packs, executive operations, cognitive OS design,
world modeling, multi-time memory, self-modeling, adaptive executive planning,
multi-runtime collaboration, distributed knowledge fabric, scientific
discovery, cognitive simulation, and a unified continuous adaptive runtime.

These layers are not authority layers. They do not browse, execute, train, call
providers, mutate memory, mutate knowledge, start schedulers, promote HYB1, or
change Model B defaults. They give future work a shared shape while preserving
the current safety boundary.

## Post-ARC XXV Exhaustive Runtime Modules

The compressed ARC VII-XXV scaffold has been expanded into dedicated,
testable runtime modules:

- `arc_07_investigation`
- `arc_08_specialists`
- `arc_09_external_evidence`
- `arc_10_tool_provider_runtime`
- `arc_11_controlled_integration`
- `arc_12_evaluation_regression`
- `arc_13_sleep_replay`
- `arc_14_domain_packs`
- `arc_15_executive_operations`
- `arc_16_cognitive_os`
- `arc_17_world_model`
- `arc_18_multitime_memory`
- `arc_19_self_model`
- `arc_20_adaptive_executive`
- `arc_21_multi_runtime_collaboration`
- `arc_22_distributed_knowledge_fabric`
- `arc_23_scientific_discovery`
- `arc_24_cognitive_simulation`
- `arc_25_continuous_runtime`

Each module has typed primitive objects, builder functions, validation,
safety-invariant reporting, audit summaries, demo payloads, report generation,
and static dashboard artifacts. The local answer path distinguishes scaffolded,
implemented-module, simulated-only, gated-future, and prohibited capabilities.

The expansion remains non-authoritative: no live provider authority, autonomous
browsing, tool execution, scheduler activation, training, memory mutation,
knowledge mutation, or HYB1 promotion is enabled.

## Post-ARC XXV Runtime Deepening

The post-ARC XXV deepening marathon moves the architecture toward robust
runtime modules without activating them. It adds 120 deterministic modules
across four batches:

- Batch A: runtime hardening
- Batch B: reasoning deepening
- Batch C: knowledge substrate deepening
- Batch D: executive deepening

Each deepening module has typed objects, builders, validators, audit helpers,
summary helpers, demo payloads, JSON export, graph export metadata, tests,
documentation, report generation, and dashboard generation.

All deepened capabilities remain `implemented_module_simulated_only` and
`gated_future_capability`. They are inspectable architecture, not authority.

## Post-ARC XXV Runtime Architecture Completion

The second post-ARC XXV overnight marathon completes the inert runtime
architecture surface across six additional batches:

- Batch E: kernel runtime integration
- Batch F: knowledge graph expansion
- Batch G: reasoning architecture expansion
- Batch H: knowledge evolution expansion
- Batch I: executive intelligence expansion
- Batch J: runtime infrastructure completion

These 210 completion modules deepen routing, lifecycle, dependency graphs,
diagnostics, serialization, graph metadata, metrics, audit surfaces, replay,
comparison, compatibility, and report generation across the existing runtime.

This is still architecture, not activation. Completion modules remain
`implemented_module_simulated_only`, `advisory_only`, and
`gated_future_capability`. They do not train, fine-tune, update models, call
providers, grant provider authority, browse autonomously, execute tools, start
schedulers or background workers, mutate memory, mutate knowledge, perform
hidden writes, promote HYB1, or change Model B defaults.

## Runtime Pathology Principle

After the post-ARC XXV completion pass, DELTA's primary risk is no longer
missing architecture vocabulary. The primary risk is incoherence from too many
safe but disconnected components.

Future work should prefer vertical integration, consumer mapping, middleware
contracts, and duplicate lifecycle consolidation over additional broad
scaffold generation. A module is not architecture-complete merely because it is
typed, tested, reportable, and safe. It must also have a clear creator,
consumer, validator, auditor, and place in an end-to-end cognitive workflow.
