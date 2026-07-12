# DELTA Post-Closure Single-Model Campaign Journal

## Execution Contract

This campaign was requested as a single TERRA-led cycle after the operator determined that application-level model switching could not occur within one continuous cycle. SOL and LUNA are therefore disciplined review roles performed by TERRA, not independently switched models. Their reports must not claim independent model execution.

## Baseline

- Branch: `codex/delta-cognitive-core`
- Baseline HEAD: `b7dd1187d2ae4ec5883c3807cd5b7c7ae8df0ecb`
- Baseline recommendation: `LIVE_RUNTIME_BEHAVIORAL_CLOSURE_READY_FOR_OPERATOR_PILOT`
- DELTA-75: excluded from this campaign
- Pre-existing dirty files: preserved and excluded from campaign staging

## Phases

| Phase | Role | Status | Notes |
| --- | --- | --- | --- |
| 0 | Grounding | COMPLETE | Baseline, dirty-tree attribution, active runtime sources, reports, and model registry inspected. |
| 1 | SOL-style audit | COMPLETE | Three confirmed repairable findings, two validation limitations, and two deferred architecture or UX observations. |
| 2 | TERRA repair and validation | COMPLETE | Consent-gated live inference, nonblocking UI turn handling, and GPU layer telemetry repairs implemented and validated. |
| 3 | LUNA-style exploration | COMPLETE | Proposal-only structural review completed after production edits were frozen. |

## Initial Evidence

- The live runtime calls `route_message(..., execute_local_model=False)` for ordinary turns.
- A live normal-chat turn can expose no pending local-model action, and a following `yes` is handled as social conversation rather than a model invocation.
- The local model registry discovers Llama and Mistral files; the controller reports lane selection and serial residency but the prior behavioral closure campaign recorded zero model calls.

## Completed Evidence

- SOL-style audit confirmed that live local inference was unreachable from the live branch and that the UI performed synchronous retrieval on the Tk event thread.
- TERRA repaired the live consent path, added model residency and controller events, moved live turns to a worker queue, and corrected process-scoped GPU layer telemetry.
- Focused validation: 97 tests passed; continuous-runtime validation: 9 tests passed against a pre-existing dirty controller file; py_compile passed.
- Full deterministic regression: 373 scenarios, 1,500 turns, 20 families, zero pathologies, and zero governance violations.
- Real-model pilot: Llama -> Mistral -> Llama executed successfully with serial residency, no provider calls, no external retrieval, and no memory writes.
- Live UI smoke: real Wikipedia retrieval accepted a queued pause; real Llama inference accepted a queued suspend; clean shutdown succeeded.
- LUNA-style review found no reason for a broad rewrite. It recommends consolidation of the live-turn coordinator, pending-action abstractions, and model-aware campaign coverage before larger autonomy work.

## Implementation Commit

- Commit: `4e5484f9`
- Message: `strengthen DELTA runtime after systems audit`
- Included: live runtime repair, UI worker bridge, provider telemetry repair, focused tests, and campaign artifacts.
- Excluded: all pre-existing dirty documentation, controller, RC report, continuity report, and unrelated test changes.
