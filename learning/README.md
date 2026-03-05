# Learning (Phase 12 — Design Only)

Status: ACTIVE (Design Only)  
Authority: NONE  
Runtime Coupling: FORBIDDEN  

---

## Purpose

This package defines the **design-time infrastructure for learning**
in the neural framework.

No learning is enabled here.

This layer exists to:
- describe *how* learning proposals are represented
- prove safety properties (idempotence, boundedness, replay consistency)
- surface learning artifacts via inspection only

---

## What Learning Is (Here)

Learning is treated as:
- offline
- replay-derived
- deterministic
- reversible
- advisory

Learning produces **descriptions of possible change**, not change itself.

---

## What Learning Is NOT

Learning does NOT:
- modify runtime state
- modify memory
- influence decisions
- influence salience, routing, or control
- persist hidden state
- self-activate

Any code doing so is a phase violation.

---

## Core Components

### Schemas
- `LearningDelta`
- `LearningProposal`
- `LearningSessionReport`

All are:
- immutable
- serializable
- discardable

### Session
- `LearningSession`
- pure transform: replay → proposals

### Audit
- `LearningAudit`
- enforces boundedness and replay consistency

### Inspection
- `LearningInspectionAdapter`
- exposes summaries only

---

## Promotion Boundary

Learning may propose.
Promotion decides.

Nothing learned is real until it:
1. survives replay
2. passes audit
3. is inspected
4. is explicitly accepted

---

## Phase Discipline

Phase 12 authorizes:
- schemas
- interfaces
- tests

Phase 12 forbids:
- execution
- mutation
- persistence

Learning logic itself comes later, or never.

That is intentional.
