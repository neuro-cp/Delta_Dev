# DELTA Invariants

This document defines rules future Delta work must preserve. These are not
roadmap items or feature goals; they are substrate invariants.

## Authority

- Experience memory is append-only.
- Knowledge is derived, never silently rewritten.
- Provenance is never lost.
- Contradictions are linked, not erased.
- Confidence changes require evidence.
- LLMs propose; Delta governs.
- Agency proposes; execution remains bounded and explicit.
- No subsystem receives hidden execution authority.

## State

- Append-only history must not be mistaken for current truth.
- Current-state metrics must resolve latest valid revisions.
- Every persistent record should remain traceable to its origin.
- Every promoted knowledge record must preserve source evidence.
- Every prediction should remain traceable through its lifecycle.
- Duplicate suppression must prevent repeated cycles from creating duplicate
  knowledge without new evidence.

## Cognition

- Every cognitive cycle should be observable.
- Every important decision should be explainable.
- Every region should have a single responsibility.
- Every subsystem should participate in the canonical cognitive cycle or remain
  clearly outside it as a tool/client.
- Interfaces such as chat, coding, automation, robotics, dashboards, and APIs
  are clients of the substrate, not the substrate itself.
- Do not optimize Delta around a single interface.

## Development

- Prefer governance, observability, reproducibility, and metric accuracy over
  adding new top-level regions.
- Treat runtime experiments as evidence.
- Reports must distinguish observed behavior from aspiration.
- Documentation must be sufficient for a cold Codex session to resume without
  rediscovering context.
