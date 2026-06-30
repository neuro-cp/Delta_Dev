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
memory may change over time through explicit consolidation and confidence
updates.

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

## Attention Principle

Attention is not retrieval.

Retrieval answers: what exists?

Attention answers: what matters right now?

Attention may use retrieved memory as one input, but it should also account for
recency, confidence, novelty, contradiction, goal relevance, task relevance,
operator priority, salience, and future nervous-system signals.

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
- non-authoritative Learning Region records
- cycle-attached learning stage producing semantic candidates, confidence
  update suggestions, questions, and goal candidates
- semantic knowledge records with provenance
- explicit semantic consolidation from learning records
- contradiction records for preserved conflicting claims
- prediction records generated from sufficiently confident knowledge
- per-cycle working memory context assembled from observation, attention,
  semantic knowledge, and predictions
- generated self-model snapshots with temporal continuity, cognitive metrics,
  and health indicators
- non-executing simulation reports over hypothetical futures
- append-only goal records
- proposed plans that survive across sessions
- explicit decision records for proposed plans
- agency proposals that answer what Delta should do next without execution

Incomplete:

- applied goal evolution from learning/reflection
- completed plan execution histories
- action beyond returning orchestration output
- applied confidence evolution
- prediction validation
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
- predictions are generated from sufficiently confident semantic records

Knowledge has no direct execution authority.

## Non-Negotiable Design Rule

Do not build isolated intelligence modules. Every new subsystem must participate
in the canonical cognitive cycle through well-defined interfaces. If a subsystem
cannot identify where it receives information from the cycle and where it
contributes back into the cycle, reconsider its design.
