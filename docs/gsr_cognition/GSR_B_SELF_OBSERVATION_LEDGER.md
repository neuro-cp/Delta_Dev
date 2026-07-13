# GSR-B Self-Observation Ledger

## Purpose

GSR-B records governed observations as inert, reviewable evidence. The ledger is a state model for operator review; it is not a monitoring loop, memory system, diagnosis engine, or repair engine.

Core boundaries:

- Observation is not judgment.
- Observation is not diagnosis.
- Diagnosis eligibility is not diagnosis creation.
- Retention is not memory persistence.
- Review authority is external and operator-controlled.

## Relationship To GSR-A

GSR-B extends the GSR-A governance spine in `orchestration/runtime/gsr_a_governed_self_regulation.py`.

It reuses GSR-A's `SelfObservation`, `GovernanceDecision` authority vocabulary, serialization helpers, stable IDs, and inert safety metadata. GSR-B remains in the same runtime file so observations, review decisions, and later diagnosis eligibility share one deny-by-default governance model instead of creating a parallel authority system.

## Contracts

### ObservationEvidence

`ObservationEvidence` records the source and provenance of a reported behavior. It includes source subsystem, source type, source reference, observed and expected transitions, first incorrect transition, evidence fingerprint, user-visible and telemetry-only distinctions, synthetic/live flags, provider/model flags, and canonical-write flags.

Its boundary is evidence capture only. It cannot authorize review, create a ledger entry by itself, diagnose a defect, or write memory.

### ObservationLedgerEntry

`ObservationLedgerEntry` is the reviewable ledger item linked to a validated `SelfObservation` and one or more evidence references. It stores lifecycle state, operator disposition, duplicate and supersession references, occurrence and corroboration counts, retention metadata, expiration metadata, and diagnosis-review eligibility status.

Its boundary is inert ledger state. Retention in the ledger is not canonical or noncanonical memory persistence.

### ObservationDisposition

`ObservationDisposition` is a recordable summary of an operator review decision. It explicitly carries operator authority, target entry, disposition, rationale, and sequence.

Its boundary is review evidence only. It does not create a diagnosis candidate, repair proposal, or write memory.

### ObservationReviewDecision

`ObservationReviewDecision` is the only way a ledger entry can receive a review disposition. It must carry operator-controlled authority, target exactly one entry, remain one-shot, and pass expiration/consumption checks.

Successful decision IDs are recorded in ledger state. Failed decisions remain unconsumed. Reused decisions fail closed.

### ObservationLedgerState

`ObservationLedgerState` is an immutable ledger snapshot containing entries, evidence index, duplicate links, supersession links, review queue, diagnosis-review queue, expired and suspended indexes, consumed review-decision IDs, and safety metadata.

It is not persistence. It does not start a scheduler, background task, provider call, model call, runtime registration, or memory write.

### ObservationLedgerResult

`ObservationLedgerResult` returns the outcome of a ledger operation: accepted flag, reason, resulting state, optional entry, and a flag proving no diagnosis candidate was created.

## Evidence Provenance

GSR-B evidence uses deterministic fingerprinting and normalized observation signatures. Evidence records preserve:

- source subsystem;
- source type and source reference;
- observed input and output;
- expected and observed transition;
- first incorrect transition;
- synthetic-fixture flag;
- live-runtime flag;
- provider/model flags;
- canonical-write flag;
- user-visible and telemetry-only distinctions.

Provider involvement, model involvement, or canonical-write evidence fails validation for ledger insertion in this inert milestone.

## Ledger Insertion

`record_observation()` validates evidence before insertion. Invalid or incomplete evidence fails closed. Valid evidence creates a `pending_review` ledger entry and adds evidence to the ledger evidence index.

Insertion does not:

- retain the entry as accepted;
- create a diagnosis;
- create a repair proposal;
- write memory;
- authorize execution.

Duplicate detection is conservative. Matching evidence fingerprints and normalized signatures can link a possible duplicate, but both entries and both evidence records remain present.

## Review Decisions

`review_observation_entry()` applies a disposition only through a valid `ObservationReviewDecision`.

Review rules:

- operator authority marker is required;
- one-shot decisions are consumed only after successful transition;
- failed decisions remain unconsumed;
- reused decision IDs fail closed;
- decision IDs survive serialization;
- consumed decisions are not reactivated by deserialization.

## Dispositions And Terminal Denial

Supported ledger lifecycle dispositions:

- `retained`
- `rejected`
- `duplicate`
- `corroborated`
- `superseded`
- `expired`
- `insufficient_evidence`
- `non_defect`
- `telemetry_only`
- `suspended`
- `diagnosis_review_eligible`

Supported review-decision disposition identifiers:

- `retain`
- `reject`
- `mark_duplicate`
- `mark_corroborated`
- `supersede`
- `expire`
- `mark_insufficient_evidence`
- `mark_non_defect`
- `mark_telemetry_only`
- `suspend`
- `make_diagnosis_review_eligible`

Terminal denial states:

- `rejected`
- `superseded`
- `expired`
- `suspended`

The lifecycle state records the current ledger position. `operator_disposition` records the operator-applied disposition. They usually match after review, but remain distinct fields for auditability.

## Deduplication And Corroboration

Deduplication uses a deterministic normalized signature plus matching evidence fingerprint, source subsystem, expected transition, observed transition, objective, and first incorrect transition.

Duplicate linking:

- preserves both entries;
- preserves both evidence records;
- does not delete or merge entries;
- does not imply diagnosis.

Corroboration increments support but remains non-diagnostic. Repetition, severity, confidence, duplicate count, and corroboration count do not create diagnosis-review eligibility.

## Retention And Expiration

Allowed retention policies:

- `retain_until_review`
- `retain_for_sequence_window`
- `retain_until_objective_closed`
- `manual_retention`
- `expire_after_sequence`

Retention policies are metadata only. Expiration occurs only through the explicit pure function `expire_observation_entries()`.

Expiration rules:

- caller supplies current sequence;
- objective-closure expiration requires explicit `objective_closed=True`;
- no wall clock is used;
- no scheduler or cleanup loop exists;
- no database or file persistence occurs;
- manual retention does not expire automatically;
- expired entries remain present and audit-visible;
- evidence is never deleted.

## Supersession

Supersession requires an explicit valid operator review decision. It must identify the superseded entry and a real, distinct replacement entry already present in the ledger.

Supersession:

- preserves both entries;
- records the supersession link;
- blocks the superseded entry from further advancement;
- leaves the replacement entry pending or otherwise unchanged;
- does not automatically approve, retain, corroborate, or diagnosis-enable the replacement.

## Diagnosis-Review Eligibility

The only valid chain is:

```text
ledger entry -> explicit operator decision -> diagnosis_review_eligible
```

The chain stops there. GSR-B does not create a `DiagnosisCandidate`, create a `RepairProposal`, request a sandbox, advance a GSR-A regulation cycle, or instantiate any execution path.

Telemetry-only evidence cannot become diagnosis-review eligible directly. It requires a telemetry-only disposition and a separate explicit reclassifying operator decision.

## Serialization

Serialization preserves:

- evidence provenance;
- duplicate links;
- supersession links;
- terminal states;
- retention metadata;
- expiration metadata;
- consumed review-decision IDs;
- diagnosis-review queue;
- safety flags;
- telemetry, synthetic-fixture, live-runtime, provider, and model flags.

Deserialization does not reactivate used decisions, clear terminal states, lose evidence, create diagnoses, create proposals, execute expiration, or perform persistence.

## Non-Capabilities

GSR-B does not provide:

- continuous monitoring;
- autonomous observation generation;
- diagnosis generation;
- repair proposals;
- authorization;
- execution;
- persistence;
- canonical memory writes;
- noncanonical memory writes;
- background tasks;
- schedulers;
- provider calls;
- local-model calls;
- live-router integration;
- `DELTA.py` integration;
- continuous-runtime integration.
