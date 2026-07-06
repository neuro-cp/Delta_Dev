# RC1 Operator Guide

## Startup
Run local scripts from `G:\Delta_Dev` using the checked-in Python environment. Prefer deterministic scripts and reports over ad hoc mutation.

## Shutdown
Stop local consoles or scripts normally. RC1 starts no scheduler, listener, or background worker by default.

## Replay
Use replay reports as evidence. Replay does not authorize canonical writes or training.

## Rollback
Rollback handles must point to the affected record, audit trail, and pre-change state. No irreversible migration is part of RC1.

## Review
Operator review remains final for persistence and integration decisions.

## Persistence
Controlled noncanonical persistence exists; canonical promotion is not automatic.

## Evidence And Provenance
Every operational claim should cite report paths, trace ids, manifests, or reproduction steps.

## Evaluation
Treat operational observations as experiments. Record expected behavior, observed behavior, severity, and reproduction steps.

## Troubleshooting
Classify failures through `RC1_FAILURE_CLASSIFICATION`; do not add architecture until evidence identifies the bottleneck.
