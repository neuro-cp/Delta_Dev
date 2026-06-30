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
- Learning Region: proposes durable changes from experience.
- Execution Region: performs bounded actions through explicit authorization.
- Reflection Region: evaluates what changed, repeated, failed, or should be
  consolidated.

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

Incomplete:

- goals
- planning
- action beyond returning orchestration output
- applied confidence evolution
- prediction validation
- durable attention state
- live visual and auditory input
- regulable nervous-system signals

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
