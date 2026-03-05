# Semantic Query Policy — v0

Status: DRAFT  
Phase: 7A (Read-Only Semantic Access)  
Authority: NONE  
Depends On:
- semantic_policy.md
- semantic_schema.md
- semantic_update_rules.md

---

## Purpose

This policy defines **how semantic memory may be queried by cognition**.

Semantic queries provide **descriptive reference only**.
They do not guide, bias, rank, or influence decisions.

This policy exists to prevent semantic memory from becoming
a covert policy engine.

---

## Core Principle

Semantic memory may be **consulted**, never **obeyed**.

Query results describe statistical regularities.
They do not prescribe actions or priorities.

---

## Directionality

Information flow is strictly one-way:

# Semantic Query Policy — v0

Status: DRAFT  
Phase: 7A (Read-Only Semantic Access)  
Authority: NONE  
Depends On:
- semantic_policy.md
- semantic_schema.md
- semantic_update_rules.md

---

## Purpose

This policy defines **how semantic memory may be queried by cognition**.

Semantic queries provide **descriptive reference only**.
They do not guide, bias, rank, or influence decisions.

This policy exists to prevent semantic memory from becoming
a covert policy engine.

---

## Core Principle

Semantic memory may be **consulted**, never **obeyed**.

Query results describe statistical regularities.
They do not prescribe actions or priorities.

---

## Directionality

Information flow is strictly one-way:


There is NO allowed path from semantic query results to:

- Decision latch logic
- Salience modulation
- Value authorization
- Urgency signals
- Action gating
- Control persistence

---

## Allowed Query Scope

Cognition MAY query semantic memory for:

- Frequencies
- Counts
- Rates
- Distributions
- Historical regularities
- Presence or absence of patterns

Queries MUST be phrased as:

- “What tends to occur?”
- “How often has X been observed?”
- “Is pattern Y present in memory?”

---

## Forbidden Query Scope

Cognition MUST NOT query semantic memory for:

- Recommendations
- Rankings
- Preferences
- Optimal actions
- Utility estimates
- Expected rewards
- Risk assessments
- Confidence in correctness

If a query answers *“what should I do?”*,
it violates this policy.

---

## Query Timing Constraints

Semantic queries MUST:

- Occur outside decision commitment windows
- Occur outside `BrainRuntime.step`
- Occur outside active control evaluation

Allowed contexts include:

- Pre-deliberation reflection
- Post-episode analysis
- Offline reasoning
- Debugging or inspection tools

Semantic queries MUST NOT occur:

- During action selection
- During latch evaluation
- During salience/value computation

---

## Response Constraints

Semantic query responses MUST:

- Be immutable
- Be non-authoritative
- Contain no scores usable as priorities
- Contain no normalized “importance” values

Responses may include:

- Raw frequencies
- Percentages
- Counts
- Statistical descriptors

Responses MUST NOT include:

- Thresholded recommendations
- Ranked lists of actions
- Weighted preferences
- Any directive language

---

## No Caching Rule

Semantic query results:

- MUST NOT be cached inside runtime loops
- MUST NOT persist into working memory
- MUST NOT influence future decisions indirectly

Each query is treated as a **stateless lookup**.

---

## No Feedback Rule

Semantic memory MUST NOT be updated based on queries.

Query access does NOT count as evidence.
Only consolidation and replay contribute to semantic updates.

---

## Auditability

All semantic queries MUST be:

- Explicit
- Inspectable
- Logged or traceable (offline)

Hidden or implicit queries are forbidden.

---

## Explicit Prohibitions

Semantic querying MUST NEVER:

- Modify semantic records
- Modify episodic memory
- Modify consolidation artifacts
- Trigger learning
- Influence control signals
- Substitute for reasoning

If removing semantic memory changes behavior,
this policy has been violated.

---

## Invariants

At all times:

- Semantic memory remains advisory
- Semantic memory remains offline-derived
- Semantic memory remains discardable
- Semantic memory never acquires authority

These invariants supersede convenience.

---

## Phase Boundary

Completion of Phase 7A authorizes:

- Design of semantic query interfaces
- Read-only adapters
- Inspection and analysis tooling

It does NOT authorize:

- Runtime semantic influence
- Action biasing
- Preference formation

Those require a future, explicit phase.

---

End of policy.

