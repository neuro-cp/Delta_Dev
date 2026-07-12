# DELTA 1.6 Architecture

DELTA 1.6 adds a thin coordination layer over existing runtime state. It reuses DELTA 1.2 for event cycles and journaling, DELTA 1.4 for live Wikipedia state, and DELTA 1.5 for evidence comparison. Runtime autonomy remains bounded to inert local cognition.

## Implemented

- Operational self-model built from the live session, runtime state, capability state, evidence sources, pending inquiries, initiatives, and health.
- Deterministic authority evaluator with `AUTONOMOUS_SAFE`, `OPERATOR_APPROVAL_REQUIRED`, `PROHIBITED`, and `UNCLASSIFIED_FAIL_CLOSED`.
- Initiative records for useful internal observations, including novelty, value, urgency, confidence, notification class, duplicate suppression, and authority class.
- Developmental identity proposal support that can defer when evidence is insufficient and never persists automatically.
- Live chat answers for self-model questions such as current work, capabilities, uncertainty, permission boundaries, and identity status.
- Live UI pause, resume, and suspend controls for bounded initiative.

## Reuse

DELTA 1.6 does not replace the live runtime. It wraps:

- `LiveRuntimeState`, `ActivityJournal`, inquiries, notification policy, and wake cycle from DELTA 1.2.
- `WikipediaPermissionProfile` from DELTA 1.1.
- `LiveWikipediaRuntimeSession` and Wikipedia bridge from DELTA 1.4.
- `DevelopmentalCognitionResult`, promotion candidates, and operator inquiry records from DELTA 1.5.

## Authority Boundary

The runtime may perform inert local analysis and queue review items. It may not write memory, persist identity, modify code, commit, push, deploy, activate providers, expand permissions, or change governance.
