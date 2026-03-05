# Semantic Memory Policy — v0

Status: DRAFT  
Phase: 6 (Offline Semantic Memory)  
Authority: NONE  
Scope: Episodic → Semantic Compression

---

## Purpose

This policy defines the rules governing **semantic memory**.

Semantic memory is a **compressed, low-entropy summary**
of repeated episodic structure.

It describes *what tends to be true*.
It does not decide *what should be done*.

---

## Core Principle

Semantic memory is **descriptive, not prescriptive**.

It summarizes patterns across episodes.
It never issues commands, goals, or preferences.

---

## Relationship to Episodic Memory

Semantic memory is derived **only** from:

- Closed `Episode` objects
- Consolidation artifacts (Phase 5B)
- Offline replay summaries

Semantic memory MUST NOT:

- Replace episodic memory
- Delete or overwrite episodes
- Alter episode boundaries
- Reinterpret individual events

Episodes remain the source of truth.
Semantic memory is a lossy reference layer.

---

## Inputs

Semantic memory may read:

- Consolidation records
- Aggregated episodic statistics
- Replay-derived summaries
- Historical semantic records (previous versions)

Semantic memory MUST NOT read:

- Runtime state
- Population activity
- Salience, value, or urgency signals
- Decision latch state
- Control or executive state

---

## Outputs

Semantic memory may produce:

- Immutable semantic records
- Statistical regularities
- Frequency-based descriptors
- Abstracted tags or schemas
- Versioned summaries

All outputs MUST be:

- Offline-generated
- Deterministic
- Serializable
- Immutable once written
- Safe to discard and recompute

---

## Authority Constraints (Hard)

Semantic memory MUST NEVER:

- Influence decision selection
- Inject gain, bias, or salience
- Gate or suppress actions
- Create goals, preferences, or intent
- Trigger learning during runtime
- Execute during `BrainRuntime.step`

Semantic memory is **advisory-only**.
It cannot act.

---

## Temporal Constraints

Semantic memory updates:

- Occur offline only
- Run during rest, idle, or batch phases
- Are explicitly triggered (never implicit)

Semantic memory MUST NOT:

- Update continuously
- Update during active episodes
- React to real-time signals

---

## Stability & Update Rules

Semantic memory is **slow-changing**.

Updates MUST:

- Aggregate across many episodes
- Require repeated evidence
- Favor stability over recency
- Be robust to noise or outliers

Single episodes MUST NOT:
- Create semantic facts
- Override existing summaries

---

## Identity & Ownership

Semantic memory records:

- Do NOT represent beliefs
- Do NOT represent commitments
- Do NOT persist executive state
- Do NOT encode self-identity

They are references, not truths.

---

## Versioning

All semantic memory logic MUST declare:

- Policy version
- Record schema version

Breaking changes require:

- New policy version
- Offline migration logic
- Explicit tests

---

## Prohibited Shortcuts

The following are explicitly forbidden:

- Embedding semantic memory directly into decision logic
- Using semantic memory as a reward proxy
- Treating semantic memory as “knowledge” with authority
- Allowing semantic memory to bias salience or value
- Letting semantic memory outlive its provenance

If semantic memory can change behavior directly,
this policy has been violated.

---

## Future Work (Non-Binding)

Potential future extensions:

- Schema induction
- Concept clustering
- Episodic → semantic promotion thresholds
- Forgetting and decay policies

All extensions must remain:

- Offline
- Read-only with respect to runtime
- Non-authoritative

---

End of policy.
